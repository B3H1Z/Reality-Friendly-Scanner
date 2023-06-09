import re
import requests
import urllib.request
import socket
import ssl
from alive_progress import alive_bar
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from termcolor import colored
import tldextract

URL_MAIN = "https://bgp.tools"
URL_ROUTE = "/prefix"
URL = URL_MAIN + URL_ROUTE
TIMEOUT = 3


def send_request(ip):
    ua = UserAgent()
    header = {
        'User-Agent': ua.random,
    }

    try:
        res_try = requests.get(URL_MAIN, headers=header, timeout=5)
        if res_try.status_code == 403:
            print(colored("Your IP BLOCKED by bgp.tools", "red"))
            return False
    except requests.exceptions.RequestException as e:
        print(colored("Cannot connect to bgp.tools \n Check your internet connection", "red"))
        return False

    try:
        res = requests.get(
            f"{URL}/{ip}", headers=header, timeout=TIMEOUT
        )
    except requests.exceptions.RequestException as e:
        print(colored("Cannot connect to bgp.tools \n Please try again", "red"))
        return False

    return res


def cipher_checker(domain):
    context = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                ssock_version = ssock.version()
                ssock_cipher = ssock.cipher()
        return ssock_cipher
    except Exception:
        pass


def domain_ip_range_checker(domain):
    ip = socket.gethostbyname(domain)
    if ip:
        return ip


def domain_checker(domain):
    domain = str(domain).replace(" ", "")
    domain_s = f"https://{domain}"
    try:
        status = urllib.request.urlopen(domain_s, timeout=TIMEOUT)
        status = status.getcode()
        if status == 200:
            ssock_cipher = cipher_checker(domain)
            ssock_version = ssock_cipher[1]
            if ssock_version == "TLSv1.3":
                dns = domain_ip_range_checker(domain)
                print(colored(f"{domain} => {ssock_cipher} => {dns}", "green"))
            else:
                print(colored(f"{domain} => {ssock_cipher}", "red"))
    except Exception:
        pass


def check_useless_domain(url):
    regex_ip_in_domain = r'(?:[0-9]{1,3}\-){2}[0-9]{1,3}|(?:[0-9]{1,3}\.){2}[0-9]{1,3}'
    regex_subdomain = r'[.-]'
    if not re.findall(regex_ip_in_domain, url):
        ext = tldextract.extract(url)
        if not re.search(regex_subdomain, ext[0]):
            if not ext[0] == 'mail':
                return True
            else:
                return False
        else:
            return False
    else:
        return False


def fdns_html_parser(html):
    domains = []
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='fdnstable')
    if not table:
        colored('Forward DNS table not found', "yellow")
        return False

    all_tr = table.findAll('tr')
    all_tr.pop(0)

    for tr in all_tr:
        _domain = tr.find('td', {'class': 'smallonmobile nowrap'})
        if _domain.text:
            _domain = _domain.text
            # Forward DNS Split multi urls
            if _domain.find(",") != -1:
                _domain = _domain.split(",")
                for domain in _domain:
                    domain = domain.replace(" ", "")
                    if domain.find('(') != -1:
                        domain = domain.split("(")[0]
                    domain = domain.replace(" ", "").strip()
                    domains.append(domain)
            else:
                domains.append(_domain)
    return domains


def rdns_html_parser(html):
    domains = []
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='rdnstable')
    if not table:
        return False

    all_tr = table.findAll('tr')
    all_tr.pop(0)

    for tr in all_tr:
        _domain = tr.find('td', {'class': 'smallonmobile nowrap'})
        if _domain.text[-1] == ".":
            _domain = _domain.text[:-1]
        else:
            _domain = _domain.text

        domains.append(_domain)
    return domains


def validate_ipv4_address(address):
    ipv4_pattern = "^(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    status = re.match(ipv4_pattern, address)
    return status


if __name__ == '__main__':

    input_ip = input(colored("Please enter your server ip: ", "cyan"))

    if validate_ipv4_address(input_ip):
        print("Waiting for getting data from bgp.tools ...")
        html_response = send_request(input_ip)
        if html_response:
            rdns_domains = rdns_html_parser(html_response.text)

            print("Checking Reversed Dns Domains ...")

            if rdns_domains:
                with alive_bar(len(rdns_domains), force_tty=True) as bar:
                    for rdomain in rdns_domains:
                        if check_useless_domain(rdomain):
                            domain_checker(rdomain)
                        bar.text(rdomain)
                        bar()
            else:
                print(colored("Reverse DNS Domains not found!", "yellow"))
            print("Checking Forward Dns Domains ...")
            fdns_domains = fdns_html_parser(html_response.text)
            if fdns_domains:
                with alive_bar(len(fdns_domains), force_tty=True) as bar:
                    for fdomain in fdns_domains:
                        if check_useless_domain(fdomain):
                            domain_checker(fdomain)
                        bar.text(fdomain)
                        bar()
            else:
                print(colored("Forward DNS Domains not found!", "yellow"))

            print(colored("Done!", "green"))
    else:
        print(colored("Please Enter Valid ipv4 address", "red"))
