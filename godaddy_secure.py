import configparser
import requests
import os
from datetime import datetime, timezone, timedelta
import time

def check_create_config():
    """Check for the existence of the config.ini file and create it if not found."""
    config_file = 'config.ini'
    if not os.path.exists(config_file):
        config = configparser.ConfigParser()
        config['GODADDY'] = {
            'API_KEY': 'your_api_key_here',
            'API_SECRET': 'your_api_secret_here',
            'LOG_FILE': 'ip_change_log.txt'
        }
        config['RECORDS'] = {
            'example.com': '@',
            'sub.example.com': 'A'
        }
        with open(config_file, 'w') as configfile:
            config.write(configfile)
        print(f'Configuration file {config_file} created. Please edit it with your details before running the script again.')
        exit()

def utc_to_ist(utc_dt):
    """Convert UTC datetime to IST datetime."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=ist)

def get_current_ip():
    """Fetch the current public IP address."""
    try:
        response = requests.get('https://api.ipify.org?format=json')
        response.raise_for_status()
        return response.json().get('ip')
    except requests.RequestException as e:
        print(f"Error fetching current IP: {e}")
        return None

def update_dns_record(ip, headers, domain):
    """Update the DNS A record for the specified domain."""
    url = f'https://api.godaddy.com/v1/domains/{domain}/records/A/@'
    data = [{'data': ip, 'ttl': 600}]
    try:
        response = requests.put(url, json=data, headers=headers)
        response.raise_for_status()
        print(f'Successfully updated DNS record to {ip} for {domain}')
    except requests.RequestException as e:
        print(f'Failed to update DNS record for {domain}: {e}')

def get_last_known_ip(log_file):
    """Read the last known IP address from the log file."""
    try:
        with open(log_file, 'r') as file:
            lines = file.readlines()
            if lines:
                last_line = lines[-1]
                last_ip = last_line.split(' - ')[-1].strip()
                return last_ip
            return None
    except FileNotFoundError:
        return None

def log_current_ip(ip, log_file):
    """Log the current IP address with a timestamp."""
    timestamp = datetime.now()
    timestamp_ist = utc_to_ist(timestamp).strftime('%Y-%m-%d %H:%M:%S %Z')
    with open(log_file, 'a') as file:
        file.write(f'{timestamp_ist} - {ip}\n')

def load_config():
    """Load configuration from config.ini, trimming any leading/trailing spaces."""
    config = configparser.ConfigParser()
    config.read('config.ini')
    settings = config['GODADDY']
    
    GODADDY_API_KEY = settings['API_KEY'].strip()
    GODADDY_API_SECRET = settings['API_SECRET'].strip()
    LOG_FILE = settings['LOG_FILE'].strip()
    
    return GODADDY_API_KEY, GODADDY_API_SECRET, LOG_FILE

def main():
    check_create_config()
    GODADDY_API_KEY, GODADDY_API_SECRET, LOG_FILE = load_config()
    
    headers = {
        'Authorization': f'sso-key {GODADDY_API_KEY}:{GODADDY_API_SECRET}',
        'Content-Type': 'application/json',
    }

    current_ip = get_current_ip()
    if current_ip is None:
        return

    config = configparser.ConfigParser()
    config.read('config.ini')
    records = config['RECORDS']

    for domain, _ in records.items():
        last_ip = get_last_known_ip(LOG_FILE)
        if current_ip != last_ip:
            update_dns_record(current_ip, headers, domain)
            log_current_ip(current_ip, LOG_FILE)
        else:
            print(f'IP address has not changed ({current_ip}) for {domain}. No update required.')

    time.sleep(300)  # Adjust as needed

if __name__ == '__main__':
    main()
