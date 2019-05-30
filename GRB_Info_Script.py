'''
Author: Adam Dressel

 GRB(Gamma Ray Burst) script. The following code scrapes data from NASA's circular archive
 and formats data into an organized table. This allows researchers to gather useful information
 for identifying Gamma Ray Bursts precursors for GRBs observed by the swift telescope.
 
Swift Info - https://swift.gsfc.nasa.gov/
TESS Info - https://www.nasa.gov/tess-transiting-exoplanet-survey-satellite
TESScut Api source - https://mast.stsci.edu/tesscut/

'''

import numpy as np
import astropy as ap
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import sys
from datetime import datetime
from dateutil.parser import parse

sys.setrecursionlimit(10000)

# Following takes NASA circular webpage and turns it 
# into a Beautiful Soup object that can be used to match certain requirements

circ_Arch = requests.get('https://gcn.gsfc.nasa.gov/gcn/gcn3_archive.html')
circ_soup = BeautifulSoup(circ_Arch.text, 'html.parser')

circ_soup.prettify

# Regular Expressions for categorizing the elements in the circular list
# id_re returns the GRB and its number.
# obs_desc returns the description of the observation
# sn_re returns the serial numbers of each circular.

swift_re = re.compile(r'.*Swift detection.*')
id_re = re.compile(r'\D\D\D \d\d\d\d\d\d\D:')
obs_desc = re.compile(r'Swift.*')
sn_re = re.compile(r'(\d\d\d\d\d)')

# The circulars are sectioned in an unordered list.
circ_list = circ_soup.find('ul')

#Each element in the unordered list contains a circular link, an identifier and what made the observation.
# Circ_text is each li element in a text format.
circ_text = circ_list.find_next('li').get_text()

swift_obs = swift_re.findall(circ_text)

# This cell produced a preliminary table. The proper data set is in the following cells

# This for loop creates a list of the grb identifiers that fall under the swift observations.
i = 0
grb_ids = []
desc_list = []
sn_list = []

#element is one line in the swift obs that contains the circular #, identifier and observation description
for element in swift_obs:
    grb_ID = id_re.findall(element)
    desc = obs_desc.findall(element)
    sn = sn_re.findall(element)
    # Some empty lists are in the original ul tag so these are skipped
    if len(grb_ID) == 0:
        continue
    else:
        grb_ids.append(grb_ID[0]) #Using index notation to append the string element instead of a list object.
        desc_list.append(desc[0])
        sn_list.append(sn[0])

# The circular list is converted to a string and passed through the swift reg exp.
# Useful for navigating through desired swift ciculars, and extracting desired tags.
ul_array = swift_re.findall(str(circ_list))
# Regular expression for all href link names
gcn_re = re.compile(r'gcn3.*gcn3')

#Following code filters out the circular links from the tags, and puts them into a list.
href_list = []
for li in ul_array:
    gcn = gcn_re.findall(li)
    href_list.append(gcn[0])

# Every circular link has the following string preceding its circular number.
link = "https://gcn.gsfc.nasa.gov/"

#Each string in href_list is appended to link to create the full gcn link for the corresponding observation.
# These are then appended to link_list.
link_list = []
for circular in href_list:
    link_gcn = link + circular #Main link + corresponding circular string
    link_list.append(link_gcn)
    
gcn_text = []
#Each complete circular address in link_list is requested and converted into string format.
# These strings are then appended to a list, so that each circular can be parsed through
# to find coordinates and dates.
for gcn in link_list:
    link_src = requests.get(gcn)
    gcn_circ = link_src.text
    gcn_text.append(gcn_circ)

#Regular expressions for date, RA, DEC and identifiers
date_re = re.compile(r'\d\d.*GMT')
cord_re = re.compile(r'RA, Dec.*\d\d\d')


#Lists for each category
date_list = []
cord_list = []
id_list = []

for text in gcn_text:
    date = date_re.findall(text)
    cord = cord_re.findall(text)
    i_d = id_re.findall(text)
    
    # If else statement to overlook any empty lists, which will skip over duplicate identifiers.
    if len(i_d) == 0:
        continue
    else:
        date_list.append(date[0])
        cord_list.append(cord)
        id_list.append(i_d)
         

# Creates a table from the lists made in the previous cell.
pd.DataFrame(list(zip(id_list, cord_list, date_list, link_list)), columns= ["ID", "RA, Dec", "Date", "Circular"])

# Regular expression for parsing coordinates and their labels.
ra_exp = re.compile('RA')
dec_exp = re.compile('Dec')
cord_exp = re.compile(r'\-?\d?\d?\d.\d\d\d')

ra_list = []
dec_list = []

for cord in cord_list:
    ra_cord = cord_exp.findall(cord[0])[0] # First match in each coordinate element is ra
    dec_cord = cord_exp.findall(cord[0])[1]# Second match in each coordinate element is dec
    
    ra_list.append(ra_cord)
    dec_list.append(dec_cord)

# Results from tesscut api are appended to the following lists.
sec_list = []
sec_names = []
sec_cams = []
ccd_list = []


for i in range(0,65):
    payload = {'ra': ra_list[i], 'dec': dec_list[i], 'radius':'1m'}
    r = requests.get('https://mast.stsci.edu/tesscut/api/v0.1/sector', params = payload)
    
    #Result is a list and returns the values generated by the tesscut api.
    result = r.json()['results']
    
    # Certain coordinates do not return any sector results, filtered out and
    # A N/A value is returned to a list using an if else statement.
    
    if len(result) == 0:
        sec_list.append('N/A')
        sec_names.append('N/A')
        sec_cams.append('N/A')
        ccd_list.append('N/A')
    elif len(result) == 1:
        sec_list.append(result[0]['sector'])
        sec_names.append(result[0]['sectorName'])
        sec_cams.append(result[0]['camera'])
        ccd_list.append(result[0]['ccd'])
    else:
        sec_list.append(result[0]['sector'] + " " + result[1]['sector'])
        sec_names.append(result[0]['sectorName'] + " " + result[1]['sectorName'])
        sec_cams.append(result[0]['camera'] + " " + result[1]['camera'])
        ccd_list.append(result[0]['ccd'] + " " + result[1]['ccd'])

big_table = pd.DataFrame(list(zip(id_list, cord_list, date_list, link_list,sec_list, sec_names, sec_cams, ccd_list)), 
             columns= ["ID", "RA, Dec", "Swift Date", "Circular", "Sector", "SectorName", "Camera", "ccd"])

# The list of sectors and their start and end dates are stored in the dictionary sec_date.
sec_date = {"Sec9" : ["2019-02-28", "2019-03-25"], "Sec8" : ["2019-02-02", "2019-02-27"],
            "Sec7" : ["2019-01-08", "2019-02-01"], "Sec6" : ["2018-12-12", "2019-01-06"], 
            "Sec5" : ["2018-11-15", "2018-12-11"], "Sec4" : ["2018-10-19", "2018-11-14"], 
            "Sec3" : ["2018-09-20", "2018-10-17"], "Sec2" : ["2018-08-23", "2018-09-20"], 
            "Sec1" : ["2018-07-25", "2018-08-22"]}

#Grabs the dates column from the big table.
swift_arr = big_table['Swift Date']

#List of tess sector dates as datetime objects.
# Each sector is in a list, containing its beg and end dates.
tess_dt = []

#Converts sec_date values to datetime objects
for dates in sorted(sec_date.values()):
    dates[0] = (datetime.strptime(dates[0], "%Y-%m-%d")) #sector beginning date
    dates[1] = (datetime.strptime(dates[1], "%Y-%m-%d")) #sector end date  
    tess_dt.append(dates)

# Loop chops off timezone for conversion to datetime object.
# Converted to new list and appended to swift_dt list.
swift_dt = []
for swift_date in swift_arr:
    swift_date = (datetime.strptime(swift_date[0:8], "%y/%m/%d"))
    swift_dt.append(swift_date)
print(tess_dt)

# List grabs sectors from big_table - related sectors 
sectors = big_table['Sector']
# Convert sectors to integers, used to iterate through tess_dt dictionary by sector.
sec_ints = []
for sec in sectors:
    if sec[0] == '0':
        sec = int(sec[:4])
        sec_ints.append(sec)
    else:
        sec = sec[:4]
        sec_ints.append(sec)

# Iterate through the dates of the corresponding sectors of tess.
# Used to compare tess dates with swift dates.
rel_sec = []
for sec_num in sec_ints:
    if type(sec_num) == int:
        rel_sec.append(tess_dt[sec_num - 1])
        
    else:
        rel_sec.append("N/A")

# Swift count is used to iterate through swift_dt simultaneously with the rel_sec loop
# This is so the differences in dates can be appended to a list.
swift_count = 0

# List of tess start and end date differences
strt_diffs = []
end_diffs = []

for date in rel_sec:
    if len(date) == 2:
        start_diff = swift_dt[swift_count] - date[0] # Difference between swift observation and tess sector beg date
        end_diff = swift_dt[swift_count] - date[1] # "                                            " end date
        strt_diffs.append(start_diff)
        end_diffs.append(end_diff)
    else:
        strt_diffs.append("N/A")
        end_diffs.append("N/A")
    swift_count += 1
    
print(len(strt_diffs))

# Complete GRB Information Table.
bigger_table = pd.DataFrame(list(zip(id_list, cord_list, date_list, link_list,sec_list, sec_names, sec_cams, ccd_list,
                                    strt_diffs, end_diffs)), 
             columns= ["ID", "RA, Dec", "Swift Date", "Circular", "Sector", "SectorName", "Camera", "ccd", 
                       "Difference between TESS sector start date and Swift Obs Date", 
                       "Difference between TESS sector end date and Swift Obs Date"])
bigger_table.to_html("GRB_Table.html")
