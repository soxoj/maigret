import requests

class ParsingActivator:
    @staticmethod
    def twitter(site, logger):
        headers = dict(site.headers)
        del headers['x-guest-token']
        r = requests.post(site.activation['url'], headers=headers)
        logger.info(r)
        j = r.json()
        guest_token = j[site.activation['src']]
        site.headers['x-guest-token'] = guest_token

    @staticmethod
    def vimeo(site, logger):
        headers = dict(site.headers)
        if 'Authorization' in headers:
            del headers['Authorization']
        r = requests.get(site.activation['url'], headers=headers)
        jwt_token = r.json()['jwt']
        site.headers['Authorization'] = 'jwt ' + jwt_token
