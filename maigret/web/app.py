# app.py
from flask import Flask, render_template, request, send_file, Response, flash
import logging
import asyncio
import os
from datetime import datetime
import maigret
from maigret.sites import MaigretDatabase
from maigret.report import generate_report_context

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Configuration
MAIGRET_DB_FILE = os.path.join('maigret', 'resources', 'data.json')
COOKIES_FILE = "cookies.txt"
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

def setup_logger(log_level, name):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    return logger

async def maigret_search(username, options):
    logger = setup_logger(logging.WARNING, 'maigret')
    
    try:
        db = MaigretDatabase().load_from_path(MAIGRET_DB_FILE)
        sites = db.ranked_sites_dict(top=int(options.get('top_sites', 500)))
        
        results = await maigret.search(
            username=username,
            site_dict=sites,
            timeout=int(options.get('timeout', 30)),
            logger=logger,
            id_type=options.get('id_type', 'username'),
            cookies=COOKIES_FILE if options.get('use_cookies') else None,
        )
        
        return results
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        raise

async def search_multiple_usernames(usernames, options):
    results = []
    for username in usernames:
        try:
            search_results = await maigret_search(username.strip(), options)
            results.append((username.strip(), options['id_type'], search_results))
        except Exception as e:
            logging.error(f"Error searching username {username}: {str(e)}")
    return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    usernames_input = request.form.get('usernames', '').strip()
    if not usernames_input:
        return render_template('index.html', error="At least one username is required")
    
    try:
        # Split usernames by common separators
        usernames = [u.strip() for u in usernames_input.replace(',', ' ').split() if u.strip()]
        
        # Create timestamp for this search session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join(REPORTS_FOLDER, f"search_{timestamp}")
        os.makedirs(session_folder, exist_ok=True)
        
        # Collect options from form
        options = {
            'top_sites': request.form.get('top_sites', '500'),
            'timeout': request.form.get('timeout', '30'),
            'id_type': request.form.get('id_type', 'username'),
            'use_cookies': 'use_cookies' in request.form,
        }
        
        # Run search asynchronously for all usernames
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        general_results = loop.run_until_complete(search_multiple_usernames(usernames, options))
        
        # Save the combined graph in the session folder
        graph_path = os.path.join(session_folder, "combined_graph.html")
        maigret.report.save_graph_report(graph_path, general_results, MaigretDatabase().load_from_path(MAIGRET_DB_FILE))
        
        # Save individual reports for each username
        individual_reports = []
        for username, id_type, results in general_results:
            report_base = os.path.join(session_folder, f"report_{username}")
            
            # Save reports in different formats
            csv_path = f"{report_base}.csv"
            json_path = f"{report_base}.json"
            pdf_path = f"{report_base}.pdf"
            html_path = f"{report_base}.html"
            
            context = generate_report_context(general_results)
            
            maigret.report.save_csv_report(csv_path, username, results)
            maigret.report.save_json_report(json_path, username, results, report_type='ndjson')
            maigret.report.save_pdf_report(pdf_path, context)
            maigret.report.save_html_report(html_path, context)

            # Extract claimed profiles
            claimed_profiles = []
            for site_name, site_data in results.items():
                if (site_data.get('status') and 
                    site_data['status'].status == maigret.result.MaigretCheckStatus.CLAIMED):
                    claimed_profiles.append({
                        'site_name': site_name,
                        'url': site_data.get('url_user', ''),
                        'tags': site_data.get('status').tags if site_data.get('status') else []
                    })
            
            individual_reports.append({
                'username': username,
                'csv_file': os.path.relpath(csv_path, REPORTS_FOLDER),
                'json_file': os.path.relpath(json_path, REPORTS_FOLDER),
                'pdf_file': os.path.relpath(pdf_path, REPORTS_FOLDER),
                'html_file': os.path.relpath(html_path, REPORTS_FOLDER),
                'claimed_profiles': claimed_profiles,
            })
        
        return render_template(
            'results.html',
            usernames=usernames,
            graph_file=os.path.relpath(graph_path, REPORTS_FOLDER),
            individual_reports=individual_reports,
            timestamp=timestamp
        )
        
    except Exception as e:
        logging.error(f"Error processing search: {str(e)}", exc_info=True)
        return render_template('index.html', error=f"An error occurred: {str(e)}")

@app.route('/reports/<path:filename>')
def download_report(filename):
    """Serve report files"""
    try:
        return send_file(os.path.join(REPORTS_FOLDER, filename))
    except Exception as e:
        logging.error(f"Error serving file {filename}: {str(e)}")
        return "File not found", 404

#@app.route('/view_graph/<path:graph_path>')
#def view_graph(graph_path):
#    """Serve the graph HTML directly"""
#    graph_file = os.path.join(REPORTS_FOLDER, graph_path)
#    try:
#        with open(graph_file, 'r', encoding='utf-8') as f:
#            content = f.read()
#        return content
#    except Exception as e:
#        logging.error(f"Error serving graph {graph_file}: {str(e)}")
#        return "Error loading graph", 500

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app.run(debug=True)