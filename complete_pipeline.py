# -*- coding: utf-8 -*-
"""
Created on Wed Aug 14 13:11:26 2024

@author: e308458
"""

from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
import time
from openai import AzureOpenAI
import ast
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv
import os
import json
import pandas as pd
#selelium
options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

# OpenAI Client
AZURE_OPENAI_API_KEY=""
AZURE_OPENAI_ENDPOINT=""
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY, 
    api_version="2023-07-01-preview",
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)


def calculate_ai_costs(response, prompt_token_cost = 0.000150, completion_token_cost = 0.0006):
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens
    total_cost = ((prompt_tokens /1000) * prompt_token_cost) + ((completion_tokens/1000)* completion_token_cost)
    return total_cost

def get_page_html(url):
    # URL to scrape
    #url = 'https://www.telecompetitor.com/tag/rural-broadband/'
    driver.get(url)
    time.sleep(5)  # Wait for the page to fully load
    # Get the HTML content of the page
    html_content = driver.page_source
    return html_content


def parse_links_from_html_page(html_content, url):
    soup = BeautifulSoup(html_content, 'html.parser')
    links = []
    for link in soup.find_all('a'):
        link_text = str(link.string)
        link_url = str(link.get('href'))
        # get the base url dynamically
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        full_url = urljoin(base_url, link_url)
        
        links.append({'link_text':link_text, 'link_url':full_url})
    return links




def choose_links_ai(link_list): #2
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """You are a helpful assistant tasked with choosing links that are about broadband grants or funding recieved. Use the link text and the url to find relevant links. Please only grab the links to articles relevant to grants or funding awarded to companies. Only grab links to articles and not home, category, or tag pages. My company wants to sell products to companies that are awarded grants so we are most interested in articles that mention which companies were awarded grants or funding. Please provide a python list of links. Only provide the python list and nothing else like this: ['exampleLink1', 'exampleLink2',] I will be using ast.literal_eval() to turn the output into a list so please make sure it is a proper list. """},
                {"role": "user", "content": f""" Please extract and provide a python compatible list of links relevant to grants and funding awarded from this list: {link_list}""" }])
        result = response.choices[0].message.content.strip()
        total_cost = calculate_ai_costs(response)
        return result, total_cost
    except Exception as e:
        print('sorry, cant find links ')
        print(e)
        return [], 0


def parse_web_page_body_to_text(html_content):
    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    content_string = ''
    for content in soup.find_all('body'):
        content_string = content_string + ' ' + content.text
    links = []
    return content_string

def eliminate_noise_from_text_ai(content_string): #4
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant tasked with cleaning and eliminating noise from web scraped text. You will be provided text from the body of a webpage. Please return only the main article text and eliminate any ads, newsletter sign-ups, or related article sections. If you are not sure if the text should be deleted then play it safe and return that text too. Any text about press releases or additional details should be included in the returned text."},
                {"role": "user", "content": f""" Please remove text that isnt part of the main article from this webpage: {content_string}""" }])
        result = response.choices[0].message.content.strip()
        total_cost = calculate_ai_costs(response)
        return result, total_cost
    except Exception as e:
        print('Failed to clean text with AI: ', e)
        return 'sorry the AI model failed here', 0

def match_links_to_article_text(text, link):
    return link.lower() in text.lower()

def get_link_clean_text(url):
    html_content = get_page_html(url)
    body_text = parse_web_page_body_to_text(html_content)
    clean_body_text, total_cost = eliminate_noise_from_text_ai(body_text)
    return clean_body_text, total_cost

def calculate_ai_costs(response, prompt_token_cost = 0.000150, completion_token_cost = 0.0006):
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens
    total_cost = ((prompt_tokens /1000) * prompt_token_cost) + ((completion_tokens/1000)* completion_token_cost)
    return total_cost
    
def extract_leads_from_text(text):
    
    given_text = text
    
    print(' ---------------- text received --------------- ')
    print(' ---------------- please wait for AI --------------- ')
    prompt = f"""
    Read the following article and extract information about broadband project grants. Format the extracted information into JSON with the fields: State, Program, Release date, Funding, Miles, Subscribers, Title, Company, DBA, Service Area, State/Federal.
    
    BE SURE TO EXRTRACT ALL POSSIBLE COMPANIES THAT WERE AWARDED GRANTS EVEN IF THE FUNDING IS NOT LISTED.

    The funding information should be for what the specific company was awarded and not the total program funding amount.
    
    The output should be in the following JSON format, please don't label it as JSON. ONLY INCLUDE WHAT IS BETWEEN THE BRACKETS [] DO NOT INCLUDE QUOTATIONS. Please dont include an explanation. I will be converting it to a python dict later:
        
    [
    {{
        "State": "KS",
        "Program": "CPF",
        "Release date": "05/14/2024",
        "Funding": "$2,487,809",
        "Miles": "1643",
        "Subscribers": "1,000",
        "Title": "CPF: Broadband Infrastructure 2023"
        "Company": "Charter Communications",
        "DBA": "Spectrum",
        "Service Area": "Kiowa County",
        "State/Federal": "Federal"
    }},
    {{
        "State": "KS",
        "Program": "CPF",
        "Release date": "05/14/2024",
        "Funding": "$3,880,706",
        "Miles": "65",
        "Subscribers": "1,000",
        "Title": "CPF: The Broadband Acceleration Grant Program Year 3"
        "Company": "AT&T",
        "DBA": "AT&T Southwest",
        "Service Area": "Harvey County",
        "State/Federal": "Federal"
    }},
     {{
        "State": "ME",
        "Program": "CPF",
        "Release date": "05/18/2024",
        "Funding": "$3,640,503",
        "Miles": "12",
        "Subscribers": "1,000",
        "Title": "CPF: Connect the Ready: Cohort 1 Awards"
        "Company": "Matrix Design Group",
        "DBA": "Matrix Design Group",
        "Service Area": "Franklin County",
        "State/Federal": "Federal"
    }},
    ...
    ]

    
    Use the following article for extracting information:
        
        ---- start of text ----
    {given_text}
        ---- end of text ----
        Extract all companies even if they have missing information.
    Output the extracted information in JSON format as shown in the example above, ONLY INCLUDED WHAT IS BETWEEN THE BRACKETS.
    """

    print('api key: ', os.getenv("AZURE_OPENAI_API_KEY"))
    print('endpoint: ', os.getenv("AZURE_OPENAI_ENDPOINT"))
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
        
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )

    response = client.chat.completions.create(
        model="gpt-4", # model = "deployment_name".
        temperature=0.0,
        messages=[
                        {"role": "system", "content": """
                            You are an advanced language model trained to extract specific information from unstructured text. Your task is to identify and extract details related to project grants from articles. The extracted information should be formatted into JSON. The required fields are:
        
    1. State: Abbreviation of the state (e.g., IL, KS).
    2. Program: Abbreviation of the grant or plan or program that the funding comes from(e.g., CPF). YOU MUST USE THE LIST OF PROGRAMS MENTIONED BELOW TO CORRECTLY IDENTIFY THE PROGRAM ABBREVIATION.
    3. Release date: Date of the article (e.g., 11/28/2023).
    4. Funding: Amount awarded to the company, dollar amount only (e.g., 325000). Please provide either the total funding a company received or the indiviual grants but ONLY THE TOTAL FUNDING OR THE INDIVIDUAL GRANTS, not both. We don't want to double count. Include the most specific funding amount available.
    5. Miles: The number of miles of cable the company will be building out (e.g., 1000).
    6. Subscribers: The number of subscribers the company will be serving, also known as households or families (e.g., 1000).
    7. Title: In terms of the title creation, we are looking to have the Program (round if given):Project name. If it is a Capital Projects Fund grant, this is proceeded with a “CPF:”. For example, the first City of Fort Colins Connexion grant would be “CPF: Advance Colorado Broadband Grant Program: Poudre Park FTTP” since the round is not given. 
    8. Company: The parent company awarded the funding. Please provide the parent name if the company is a subsidiary (e.g., AT&T, not AT&T Mobility). Don't double count a parent company and a subsidiary, add them as one entry. Only add the same company if a different grant or funding was awarded to them. If a company is awarded multiple grants, list them as separate entries.
    9. DBA: The company's Doing Business As name, if applicable (e.g., Spectrum).
    10. Service Area: The counties or regions served by the company and funding.
    11. State/Federal: Whether the funding is from the state or federal government (e.g., Federal, State). YOU MUST USE THE LIST OF PROGRAMS MENTIONED BELOW TO CORRECTLY IDENTIFY IF THE PROGRAM IS STATE OR FEDERAL.
                         
    Here is a list of programs, what they are funded by, their abbreviations, and if they are a federal or state program. YOU MUST USE THIS LIST to correctly extract information: [
    {
        "State Abbreviation":"AL",
        "Program":"The Alabama Broadband Capital Projects Fund",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"AZ",
        "Program":"Arizona Broadband Development Infrastructure Grant",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"AR",
        "Program":"The Arkansas Rural Connect (ARC) Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"CA",
        "Program":"California\u2019s Last Mile Broadband Expansion",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"CO",
        "Program":"Advance Colorado Broadband",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"CT",
        "Program":"The ConneCTed Communities Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"CT",
        "Program":"Connecticut Education Network (CEN) Broadband Infrastructure Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"FL",
        "Program":"Florida\u2019s Broadband Infrastructure Program (BIP)",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"GA",
        "Program":"Georgia Capital Projects Fund",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"HI",
        "Program":"Hawaii Subsea Middle Mile Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"HI",
        "Program":"Hawaii Public Housing Authority (HPHA) Connections Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"ID",
        "Program":"The Idaho Broadband Advisory Board (IBAB) Broadband Infrastructure Grant",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"IL",
        "Program":"Connect Illinois Broadband Grant",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"IN",
        "Program":"Next Level Connections Broadband Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"IA",
        "Program":"Empower Rural Iowa Broadband Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"KS",
        "Program":"Lasting Infrastructure and Network Connectivity",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"KY",
        "Program":"Kentucky Broadband Deployment Fund",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"LA",
        "Program":"Granting Unserved Municipalities Broadband Opportunities (GUMBO)",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"ME",
        "Program":"Maine Infrastructure Ready",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MD",
        "Program":"Maryland\u2019s Network Infrastructure Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MD",
        "Program":"Connect Maryland: Broadband for Public Housing",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MD",
        "Program":"The Broadband for Difficult to Serve Premises Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MD",
        "Program":"Maryland Connected Communities Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MA",
        "Program":"Broadband Infrastructure Gap Networks Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MA",
        "Program":"Residential Internet Retrofit Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MI",
        "Program":"Realizing Opportunity with Broadband Infrastructure Networks",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MN",
        "Program":"Minnesota\u2019s Border-to-Border Broadband Development Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MN",
        "Program":"Minnesota\u2019s Line Extension Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MN",
        "Program":"The Low-Density Pilot Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MS",
        "Program":"The Broadband Expansion and Accessibility of Mississippi fund ",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MO",
        "Program":"The Missouri Broadband Infrastructure Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"MT",
        "Program":"The ConnectMT program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NE",
        "Program":"Nebraska Broadband Bridge Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NV",
        "Program":"The Nevada Middle Mile Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NH",
        "Program":"New Hampshire\u2019s Broadband Contract Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NH",
        "Program":"Broadband Matching Grant Initiative",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NJ",
        "Program":"New Jersey Broadband Infrastructure Deployment Equity",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NM",
        "Program":"The Connect New Mexico Broadband",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NY",
        "Program":"New York's Affordable Housing Connectivity Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NY",
        "Program":"Municipal Infrastructure Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NC",
        "Program":"Completing Access to Broadband",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NC",
        "Program":"Stop-Gap Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"ND",
        "Program":"Broadband North Dakota",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"OH",
        "Program":"Ohio Residential Broadband Expansion Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"OH",
        "Program":"Ohio Broadband Line Extension Customer Assistance Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"OH",
        "Program":"Shovel Ready School District Project",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"OH",
        "Program":"The Multi-County Last Mile Fiber Build Pilot Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"OH",
        "Program":"Western Ohio Infrastructure Upgrade Pilot Project",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"OK",
        "Program":"Oklahoma Broadband Infrastructure Grants Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"OR",
        "Program":"Oregon Broadband Deployment Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"PA",
        "Program":"Pennsylvania\u2019s Broadband Infrastructure Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"PR",
        "Program":"Puerto Rico Submarine Cable Resiliency Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"RI",
        "Program":"ConnectRI Broadband Deployment Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"SC",
        "Program":"Next, Next Greatest Thing | Main Street, South Carolina",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"TN",
        "Program":"Tennessee\u2019s Middle Mile Buildout and Last Mile Connection",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"TN",
        "Program":"Tennessee\u2019s Connected Community Facilities",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"TX",
        "Program":"The Bringing Online Opportunities to Texans Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"TX",
        "Program":"The Texas Rural Hospital Broadband Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"UT",
        "Program":"Utah Rural Last Mile Broadband Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"UT",
        "Program":"The Utah Department of Transportation Middle Mile Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"UT",
        "Program":"The Utah Education and Telehealth Network Infrastructure Upgrade Project",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"VT",
        "Program":"The Broadband Construction Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"VA",
        "Program":"Virginia Telecommunication Initiative (VATI)",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"WA",
        "Program":"Washington\u2019s State Broadband Office (SBO) broadband grant program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"WA",
        "Program":"Public Works Board Broadband Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"WA",
        "Program":"Community Economic Revitalization Board Rural Broadband Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"WV",
        "Program":"The West Virginia ARPA Broadband Investment Plan",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"WI",
        "Program":"Wisconsin\u2019s Broadband Infrastructure Projects Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"WY",
        "Program":"The Connect Wyoming Grant Program",
        "Funded by":"Capital Projects Fund",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"Broadband Equity, Access, and Deployment Program",
        "Funded by":"Broadband Equity, Access, and Deployment Program",
        "Program Abbreviation":"BEAD",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"Rural Development Broadband ReConnect Program",
        "Funded by":"Rural Development Broadband ReConnect Program",
        "Program Abbreviation":"RECONNECT",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"Capital Projects Fund",
        "Funded by":"American Rescue Plan Act",
        "Program Abbreviation":"CPF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"Connecting Minority Communities Program",
        "Funded by":"Connecting Minority Communities Program",
        "Program Abbreviation":"CMC",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"AL",
        "Program":"Alabama Broadband Accessibility Fund",
        "Funded by":"Alabama Broadband Accessibility Fund",
        "Program Abbreviation":"ABAF",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":null,
        "Program":"Affordable Connectivity Program Outreach Grant Program",
        "Funded by":"Affordable Connectivity Program",
        "Program Abbreviation":"ATOGP",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"NTIA Broadband Infrastructure Program",
        "Funded by":"NTIA Broadband Infrastructure Program",
        "Program Abbreviation":"BIP",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"CA",
        "Program":"CASF Broadband Infrastructure Grant",
        "Funded by":"CASF Broadband Infrastructure Grant",
        "Program Abbreviation":"CASF",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":null,
        "Program":"USDA Community Connect Grants",
        "Funded by":"USDA Community Connect Grants",
        "Program Abbreviation":"CCG",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"Community Development Block Grant \u2013 CV Small Cities and Entitlement Programs",
        "Funded by":"Community Development Block Grant \u2013 CV Small Cities and Entitlement Programs",
        "Program Abbreviation":"CDBG-CV",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"ID",
        "Program":"CFAC Broadband Grant",
        "Funded by":"CFAC Broadband Grant",
        "Program Abbreviation":"CFAC",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":"MI",
        "Program":"Connecting Michigan Communities Grant Program",
        "Funded by":"Connecting Michigan Communities Grant Program",
        "Program Abbreviation":"CMIC",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":"SD",
        "Program":"Connect South Dakota Broadband Program",
        "Funded by":"Connect South Dakota Broadband Program",
        "Program Abbreviation":"CSD",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":"VI",
        "Program":"Connect USVI",
        "Funded by":"Connect USVI",
        "Program Abbreviation":"CUSVI",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":"PR",
        "Program":"Uniendo a Puerto Rico, Bringing Puerto Rico Together",
        "Funded by":"Uniendo a Puerto Rico, Bringing Puerto Rico Together",
        "Program Abbreviation":"UPR",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":null,
        "Program":"Bipartisan Infrastructure Law Digital Equity",
        "Funded by":"Bipartisan Infrastructure Law Digital Equity",
        "Program Abbreviation":"DE",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"Emergency Connectivity Program",
        "Funded by":"Emergency Connectivity Program",
        "Program Abbreviation":"ECG",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"Empowering Rural America New ERA Program",
        "Funded by":"Inflation Reduction Act",
        "Program Abbreviation":"ERA",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"NV",
        "Program":"High Speed NV Initiative",
        "Funded by":"High Speed NV Initiative",
        "Program Abbreviation":"HSNV",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":"IN",
        "Program":"Indiana Connectivity Program",
        "Funded by":"Indiana Connectivity Program",
        "Program Abbreviation":"IN CON",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":"MA",
        "Program":"Municipal Fiber Grant Program",
        "Funded by":"Municipal Fiber Grant Program",
        "Program Abbreviation":"MFGP",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":null,
        "Program":"Enabling Middle Mile Broadband Infrastructure Program",
        "Funded by":"The Middle Mile (MM) Program",
        "Program Abbreviation":"MMBIP",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"WI",
        "Program":"Public Service Commission of Wisconsin",
        "Funded by":"Public Service Commission of Wisconsin",
        "Program Abbreviation":"PSC",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":null,
        "Program":"Public Wireless Supply Chain Innovation Fund",
        "Funded by":"Public Wireless Supply Chain Innovation Fund",
        "Program Abbreviation":"PWSCIF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"ME",
        "Program":"Regional Broadband Partners Program",
        "Funded by":"Maine Connectivity Authority's  Regional & Tribal Broadband Partners Program",
        "Program Abbreviation":"RBRP",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":null,
        "Program":"Rural Digital Opprotunity Fund",
        "Funded by":"Rural Digital Opprotunity Fund",
        "Program Abbreviation":"RDOF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"VA",
        "Program":"FRS Community Grant Program",
        "Funded by":"FRS Community Grant Program",
        "Program Abbreviation":"RSCG",
        "State\/Federal":"State"
    },
    {
        "State Abbreviation":null,
        "Program":"Tribal Broadband Connectivity Program",
        "Funded by":"Tribal Broadband Connectivity Program",
        "Program Abbreviation":"TRIBAL",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":null,
        "Program":"Coronavirus State and Local Fiscal Recovery Funds Grant Program",
        "Funded by":"American Rescue Plan Act",
        "Program Abbreviation":"SLFRF",
        "State\/Federal":"Federal"
    },
    {
        "State Abbreviation":"PA",
        "Program":"Unserved High-Speed Broadband Funding Program",
        "Funded by":"Unserved High-Speed Broadband Funding Program",
        "Program Abbreviation":"UHSB",
        "State\/Federal":"State"
    }
]

    If a field is missing, please return null as the field value.
        
    ENSURE TO EXRTRACT ALL POSSIBLE COMPANIES THAT WERE AWARDED GRANTS even if they lack other data. PLEASE GROUP BY COMPANY IF THE FUNDING SOURCE IS THE SAME. PLEASE DO NOT INCLUDE ALREADY COMPLETED PROJECTS. PLEASE DO NOT MAKE UP INFORMATION. ONLY PROVIDE DATA THAT IS WITHIN THE TEXT or return null.
    Extract all companies even if they have missing information. EXTRACT ALL POSSIBLE COMPANIES FROM THE TEXT AND THEN FILL IN THE AVAILABLE INFORMATION.
                        


                        """},
                        {"role": "user", "content": prompt}
                        ])

    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens
    print('prompt tokens: ', prompt_tokens)
    print('completion tokens: ', completion_tokens)
    print('total tokens: ', total_tokens)                                          
    text_response = response.choices[0].message.content
    print(' ---------------- text response --------------- ')
    print(text_response)
    dict_response = json.loads(text_response)
    num_entries = len(dict_response)
   



    print(' ---------------- results loaded --------------- ')
    return dict_response

url = 'https://www.telecompetitor.com/tag/rural-broadband/'

scraped_articles = []
total_cost = 0
articles_scraped = 0 
home_blog_pages_scrape = 0 

try:
    print('Getting html data from source page...')
    home_html_content = get_page_html(url)
    print('Parsing links on source page...')
    link_list = parse_links_from_html_page(home_html_content, url)
    print('Using Gen AI to filter relevant links...')
    relevant_link_list, model_cost = choose_links_ai(link_list)   #list of relevant articles
    total_cost += model_cost
    relevant_link_list = ast.literal_eval(relevant_link_list)
    print('Looping through each relevant link...')
    for link in relevant_link_list: # looping through relevant articles
        all_text = ''
        print('Getting text from article and cleaning it with Gen AI...')
        single_page_html = get_page_html(link)
        single_page_body_text = parse_web_page_body_to_text(single_page_html)
        single_page_clean_body_text, model_cost = eliminate_noise_from_text_ai(single_page_body_text)
        total_cost += model_cost
        all_text = single_page_clean_body_text
        print('Finding links on article page...')
        single_page_links = parse_links_from_html_page(single_page_html, link)
        nested_links = []
        print('Filtering only the nested links in the article text...')
        for page_link in single_page_links:
            if match_links_to_article_text(single_page_clean_body_text, page_link['link_text']): 
                nested_links.append({'link_text': page_link['link_text'], 'link':page_link['link_url']})
        relevant_nested_links, model_cost = choose_links_ai(nested_links)
        total_cost += model_cost
        relevant_nested_links = ast.literal_eval(relevant_nested_links)
        final_nested_links = []
        for relevant_nested_link in  relevant_nested_links:
            relevant_nested_link_text, model_cost = get_link_clean_text(relevant_nested_link)
            total_cost += model_cost
            all_text = all_text + ' ----------------------- ' + relevant_nested_link_text
            final_nested_links.append({'nested_url':relevant_nested_link, 'nested_text':relevant_nested_link_text})
              
        article_data = {'article_link':link, 'article_text':single_page_clean_body_text, 'final_nested_links':final_nested_links, 'combined_text':all_text}
        scraped_articles.append(article_data)
        print('----------------------------')
        print('                            ')
        print('Finished scraping article and capturing nested links')
        print('                            ')
        print('----------------------------')
        print(total_cost)
    print(total_cost)
    scraped_articles.append({'total_cost':total_cost})
        
                
            
except Exception as e:
    print('failed:', e)
finally:
    driver.quit()
    
    
for article in scraped_articles:
    if article.get('combined_text',None):
        lead_info = extract_leads_from_text(article.get('combined_text',None))
        article['leads'] = lead_info
        
        #df = pd.DataFrame(lead_info)
        #article['df']=df
    else:
        pass


