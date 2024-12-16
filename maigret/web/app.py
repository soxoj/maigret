# app.py
from flask import (
    Flask,
    render_template,
    request,
    send_file,
    Response,
    flash,
    redirect,
    url_for,
)
import logging
import os
import asyncio
from datetime import datetime
from threading import Thread
import maigret
import maigret.settings
from maigret.sites import MaigretDatabase
from maigret.report import generate_report_context

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Add background job tracking
background_jobs = {}
job_results = {}

# Configuration
MAIGRET_DB_FILE = os.path.join('maigret', 'resources', 'data.json')
COOKIES_FILE = "cookies.txt"
UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = os.path.abspath('/tmp/maigret_reports')

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


def process_search_task(usernames, options, timestamp):
    try:
        # Setup event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the search
        general_results = loop.run_until_complete(
            search_multiple_usernames(usernames, options)
        )

        # Create session folder
        session_folder = os.path.join(REPORTS_FOLDER, f"search_{timestamp}")
        os.makedirs(session_folder, exist_ok=True)

        # Save the combined graph
        graph_path = os.path.join(session_folder, "combined_graph.html")
        maigret.report.save_graph_report(
            graph_path,
            general_results,
            MaigretDatabase().load_from_path(MAIGRET_DB_FILE),
        )

        # Save individual reports
        individual_reports = []
        for username, id_type, results in general_results:
            report_base = os.path.join(session_folder, f"report_{username}")

            csv_path = f"{report_base}.csv"
            json_path = f"{report_base}.json"
            pdf_path = f"{report_base}.pdf"
            html_path = f"{report_base}.html"

            context = generate_report_context(general_results)

            maigret.report.save_csv_report(csv_path, username, results)
            maigret.report.save_json_report(
                json_path, username, results, report_type='ndjson'
            )
            maigret.report.save_pdf_report(pdf_path, context)
            maigret.report.save_html_report(html_path, context)

            claimed_profiles = []
            for site_name, site_data in results.items():
                if (
                    site_data.get('status')
                    and site_data['status'].status
                    == maigret.result.MaigretCheckStatus.CLAIMED
                ):
                    claimed_profiles.append(
                        {
                            'site_name': site_name,
                            'url': site_data.get('url_user', ''),
                            'tags': (
                                site_data.get('status').tags
                                if site_data.get('status')
                                else []
                            ),
                        }
                    )

            individual_reports.append(
                {
                    'username': username,
                    'csv_file': os.path.join(
                        f"search_{timestamp}", f"report_{username}.csv"
                    ),
                    'json_file': os.path.join(
                        f"search_{timestamp}", f"report_{username}.json"
                    ),
                    'pdf_file': os.path.join(
                        f"search_{timestamp}", f"report_{username}.pdf"
                    ),
                    'html_file': os.path.join(
                        f"search_{timestamp}", f"report_{username}.html"
                    ),
                    'claimed_profiles': claimed_profiles,
                }
            )

        # Save results and mark job as complete
        job_results[timestamp] = {
            'status': 'completed',
            'session_folder': f"search_{timestamp}",
            'graph_file': os.path.join(f"search_{timestamp}", "combined_graph.html"),
            'usernames': usernames,
            'individual_reports': individual_reports,
        }
    except Exception as e:
        job_results[timestamp] = {'status': 'failed', 'error': str(e)}
    finally:
        background_jobs[timestamp]['completed'] = True


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    usernames_input = request.form.get('usernames', '').strip()
    if not usernames_input:
        flash('At least one username is required', 'danger')
        return redirect(url_for('index'))

    usernames = [
        u.strip() for u in usernames_input.replace(',', ' ').split() if u.strip()
    ]

    # Create timestamp for this search session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logging.info(f"Starting search for usernames: {usernames}")

    options = {
        'top_sites': request.form.get('top_sites', '500'),
        'timeout': request.form.get('timeout', '30'),
        'id_type': 'username',  # fixed as username
        'use_cookies': 'use_cookies' in request.form,
    }

    # Start background job
    background_jobs[timestamp] = {
        'completed': False,
        'thread': Thread(
            target=process_search_task, args=(usernames, options, timestamp)
        ),
    }
    background_jobs[timestamp]['thread'].start()

    logging.info(f"Search job started with timestamp: {timestamp}")

    # Redirect to status page
    return redirect(url_for('status', timestamp=timestamp))


@app.route('/status/<timestamp>')
def status(timestamp):
    logging.info(f"Status check for timestamp: {timestamp}")

    # Validate timestamp
    if timestamp not in background_jobs:
        flash('Invalid search session', 'danger')
        return redirect(url_for('index'))

    # Check if job is completed
    if background_jobs[timestamp]['completed']:
        result = job_results.get(timestamp)
        if not result:
            flash('No results found for this search session', 'warning')
            return redirect(url_for('index'))

        if result['status'] == 'completed':
            # Redirect to results page once done
            return redirect(url_for('results', session_id=result['session_folder']))
        else:
            error_msg = result.get('error', 'Unknown error occurred')
            flash(f'Search failed: {error_msg}', 'danger')
            return redirect(url_for('index'))

    # If job is still running, show status page with a simple spinner
    return render_template('status.html', timestamp=timestamp)


@app.route('/results/<session_id>')
def results(session_id):
    if not session_id.startswith('search_'):
        flash('Invalid results session format', 'danger')
        return redirect(url_for('index'))

    result_data = next(
        (
            r
            for r in job_results.values()
            if r.get('status') == 'completed' and r['session_folder'] == session_id
        ),
        None,
    )

    return render_template(
        'results.html',
        usernames=result_data['usernames'],
        graph_file=result_data['graph_file'],
        individual_reports=result_data['individual_reports'],
        timestamp=session_id.replace('search_', ''),
    )


@app.route('/reports/<path:filename>')
def download_report(filename):
    try:
        file_path = os.path.join(REPORTS_FOLDER, filename)
        return send_file(file_path)
    except Exception as e:
        logging.error(f"Error serving file {filename}: {str(e)}")
        return "File not found", 404


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    app.run(debug=True)
