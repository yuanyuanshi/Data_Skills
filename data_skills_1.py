import re
from nltk.corpus import stopwords
from goose import Goose
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
import time
import requests
import random
import pandas as pd
import matplotlib.pyplot as plt

#I get these keywords from the first page search result of data scientist at indeed; they're not whole but already tell a story.
program_languages=['bash','r','python','java','c++','ruby','perl','matlab','javascript','scala','php']
analysis_software=['excel','tableau','d3.js','sas','spss','d3','saas','pandas','numpy','scipy','sps','spotfire','scikits.learn','splunk','powerpoint','h2o']
bigdata_tool=['hadoop','mapreduce','spark','pig','hive','shark','oozie','zookeeper','flume','mahout']
databases=['sql','nosql','hbase','cassandra','mongodb','mysql','mssql','postgresql','oracle db','rdbms']
overall_dict = program_languages + analysis_software + bigdata_tool + databases
# the following two functions are for webpage text processing to extract the skill keywords.    
def keywords_extract(url):
    g = Goose()
    article = g.extract(url=url)
    text = article.cleaned_text
    text = re.sub("[^a-zA-Z+3]"," ", text) #get rid of things that aren't words; 3 for d3 and + for c++
    text = text.lower().split()
    stops = set(stopwords.words("english")) #filter out stop words in english language
    text = [w for w in text if not w in stops]
    text = list(set(text))
    keywords = [str(word) for word in text if word in overall_dict]
    return keywords

#for this function, thanks to this blog:https://jessesw.com/Data-Science-Skills/    
def keywords_f(soup_obj):
    for script in soup_obj(["script", "style"]):
        script.extract() # Remove these two elements from the BS4 object
    text = soup_obj.get_text() 
    lines = (line.strip() for line in text.splitlines()) # break into line
    chunks = (phrase.strip() for line in lines for phrase in line.split("  ")) # break multi-headlines into a line each
    text = ''.join(chunk for chunk in chunks if chunk).encode('utf-8') # Get rid of all blank lines and ends of line
    try:
        text = text.decode('unicode_escape').encode('ascii', 'ignore') # Need this as some websites aren't formatted
    except:                                                          
        return                                                       
    text = re.sub("[^a-zA-Z+3]"," ", text)  
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text) # Fix spacing issue from merged words
    text = text.lower().split()  # Go to lower case and split them apart
    stop_words = set(stopwords.words("english")) # Filter out any stop words
    text = [w for w in text if not w in stop_words]
    text = list(set(text)) #only care about if a word appears, don't care about the frequency
    keywords = [str(word) for word in text if word in overall_dict] #if a skill keyword is found, return it.
    return keywords


base_url = "http://www.indeed.com"    
#change the start_url can scrape different cities.
start_url = "http://www.indeed.com/jobs?q=data+scientist&l=San+Francisco%2C+CA"
resp = requests.get(start_url)
start_soup = BeautifulSoup(resp.content)
urls = start_soup.findAll('a',{'rel':'nofollow','target':'_blank'}) #this are the links of the job posts
urls = [link['href'] for link in urls] 
num_found = start_soup.find(id = 'searchCount').string.encode('utf-8').split() #this returns the total number of results
num_jobs = num_found[-1].split(',')
if len(num_jobs)>=2:
    num_jobs = int(num_jobs[0]) * 1000 + int(num_jobs[1])
else:
    num_jobs = int(num_jobs[0])
num_pages = num_jobs/10 #calculates how many pages needed to do the scraping
job_keywords=[]
print 'There are %d jobs found and we need to extract %d pages.'%(num_jobs,num_pages)
print 'extracting first page of job searching results'
# prevent the driver stopping due to the unexpectedAlertBehaviour.
webdriver.DesiredCapabilities.FIREFOX["unexpectedAlertBehaviour"] = "accept"
get_info = True
driver=webdriver.Firefox()
# set a page load time limit so that don't have to wait forever if the links are broken.
driver.set_page_load_timeout(15)
for i in range(len(urls)):
    get_info = True
    try:
        driver.get(base_url+urls[i])
    except TimeoutException:
        get_info = False
        continue
    j = random.randint(1000,2200)/1000.0
    time.sleep(j) #waits for a random time so that the website don't consider you as a bot
    if get_info:
        soup=BeautifulSoup(driver.page_source)
        print 'extracting %d job keywords...' % i
        single_job = keywords_f(soup)
        print single_job,len(soup)
        print driver.current_url
        job_keywords.append([driver.current_url,single_job])
    
for k in range(1,num_pages+1):
#this 5 pages reopen the browser is to prevent connection refused error.
    if k%5==0:
        driver.quit()
        driver=webdriver.Firefox()
        driver.set_page_load_timeout(15)
    current_url = start_url + "&start=" + str(k*10)
    print 'extracting %d page of job searching results...' % k
    resp = requests.get(current_url)
    current_soup = BeautifulSoup(resp.content)
    current_urls = current_soup.findAll('a',{'rel':'nofollow','target':'_blank'})
    current_urls = [link['href'] for link in current_urls]
    for i in range(len(current_urls)):
        get_info = True
        try:
            driver.get(base_url + current_urls[i])
        except TimeoutException:
            get_info = False
            continue 
        j = random.randint(1500,3200)/1000.0
        time.sleep(j) #waits for a random time
        if get_info:
            soup=BeautifulSoup(driver.page_source)
            print 'extracting %d job keywords...' % i
            single_job = keywords_f(soup)
            print single_job,len(soup)
            print driver.current_url
            job_keywords.append([driver.current_url,single_job])
# use driver.quit() not driver.close() can get rid of the openning too many files error.
driver.quit()
skills_dict = [w[1] for w in job_keywords]
dict={}
for words in skills_dict:
    for word in words:
        if not word in dict:
            dict[word]=1
        else:
            dict[word]+=1
Result = pd.DataFrame()
Result['Skill'] = dict.keys()
Result['Count'] = dict.values()
Result['Ranking'] = Result['Count']/float(len(job_keywords))

Result.to_csv('San_Francisco_CA_0415.csv',index=False)