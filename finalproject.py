#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 14 10:18:52 2022

@author: laurahatt
"""

#OK - various chloropleths of state trends in variables, each with
#another chloropleth next to it that provides context

#for example - a chloropleth of background check policies,
#next to a chloropleth of criminal record rates

#or - a chloropleth of reimbrusement rates, next to a chloropleth of 
#mean wage


#I will have to use an API for at least one of those supplement chloropleths

#How will I fit a model?

#Maybe I should run a regression on each pair of chloropleths -
#Like, how well does the supplemental variable predict the CCDF outcome?

#The text analysis could come in if I make a supplemental chloropleth of
#speeches by a state governor or something, and do sentiment analysis?

import os
import pandas as pd
import geopandas
import matplotlib.pyplot as plt
from datetime import strftime
pd.set_option('display.max_columns', None)

path = r'/Users/laurahatt/Documents/GitHub/Data_Skills_2_project'
CCDF = os.path.join(path, 'CCDF_databook.xlsx')
CCDF_full = pd.ExcelFile(CCDF)

#State shapefile
state_shp = os.path.join(path, 'UI_states.shp')
state_df  = geopandas.read_file(state_shp)
state_df = state_df.astype({'state_fips':'int'})

fig, ax = plt.subplots(figsize=(5,5))
ax = state_df.plot(ax=ax, color='red', edgecolor='white');



#Reimbursement rates in each state
#Note that I'm restricting to "majority rec", 
#which includes only one provider type (usually a type of center)
#only one county per state, if multiple
#only rate for first child in a family
#not considering special rates, such as special needs, etc.
#also note year - this is FFY2020, I believe
reimburse = pd.read_excel(CCDF_full, 'ReimburseRates')
reimburse = reimburse[reimburse['MajorityRec'] == -1]
reimburse = reimburse[reimburse['EndDat'] == '9999/12/31']
reimburse = reimburse[['State', 'County', 'ReimburseRatesProviderType', 
                       'ReimburseHourly1', 'ReimburseDailyFull1', 
                       'ReimburseDailyPart1','ReimburseWeeklyFull1', 
                       'ReimburseWeeklyPart1', 'ReimburseMonthlyFull1', 
                       'ReimburseMonthlyPart1', 'Notes']]

#Multipliers
reimburse_policies = pd.read_excel(CCDF_full, 'ReimbursePolicies')
reimburse_policies = reimburse_policies[reimburse_policies['MajorityRec'] == -1]
reimburse_policies = reimburse_policies[reimburse_policies['EndDat'] == '9999/12/31']
reimburse_policies = reimburse_policies[['State', 'ReimburseMultiplier']]

#Merge rates and multipliers
reimburse_full = reimburse_policies.merge(reimburse, on='State', how='outer')

#Calculate monthly rate
#now calculate actual rate
def rate_calculator(row):
    
    if row['ReimburseMultiplier'] == 1:
        return('monthly')
    elif row['ReimburseMultiplier'] > 1 and row['ReimburseMultiplier'] <= 5:
        return('weekly')
    elif row['ReimburseMultiplier'] > 5 and row['ReimburseMultiplier'] <= 30:
        return('daily')
    elif row['ReimburseMultiplier'] >30 and row['ReimburseMultiplier'] <= 240:
        return('hourly')
    else:
        return('what?')
    
 
reimburse_full['FinalRate'] = reimburse_full.apply (lambda row: rate_calculator(row), axis=1)   
reimburse_full
 


#Current reimbursement rates in Washington State counties
#this is not enough regions for a good regression

reimburse_WA = reimburse[reimburse['State'] == 53]
reimburse_WA = reimburse_WA[reimburse_WA['EndDat'] == '9999/12/31']
reimburse_WA = reimburse_WA[reimburse_WA['ReimburseRatesProviderType'] == 'Level 1 child care centers']
reimburse_WA = reimburse_WA[['County', 'ReimburseDailyFull1']] 
reimburse_WA

counties = pd.read_excel(CCDF_full, '0_counties')
counties_WA = counties[counties['FIPSStateCode'] == 53]
counties_WA = counties_WA[['CountyID', 'CountyName']]
counties_WA.columns = ['County', 'CountyName']

reimburse_WA = counties_WA.merge(reimburse, on='County', how='outer')
reimburse_WA

#https://www.dcyf.wa.gov/sites/default/files/pubs/EPS_0004.pdf
#This PDF has the counties that correspond to regions


#Job search as eligible activity
eligcrit = pd.read_excel(CCDF_full, 'EligCriteria')
eligcrit = eligcrit[eligcrit['MajorityRec'] == -1]
eligcrit.rename(columns = {'State':'state_fips'}, inplace = True)
eligcrit = eligcrit[eligcrit['state_fips'] < 60]

def record_selector(sheet): 
    """For each state, select current record (marked 999/12/31) or most recent record."""
    
    current_records = pd.DataFrame()
    list_of_states = list(sheet['state_fips'].unique())
    for state in list_of_states:
        df = sheet[sheet['state_fips'] == state]
        if '9999/12/31' in list(df['EndDat']):
            new_row = df[df['EndDat'] ==  '9999/12/31']
            current_records = pd.concat([current_records, new_row], axis=0, ignore_index=True)
        else:
            latest_date = df['EndDat'].apply(pd.to_datetime).max()
            new_row = df.loc[df['EndDat'] == latest_date.strftime('%Y/%m/%d')] 
            current_records = pd.concat([current_records, new_row], axis=0, ignore_index=True)
    return(current_records)
        
#Minimum hours of work to be eligible
#Focusing on a single-parent household
#and minimum hours for at least part-time care 

minhours = record_selector(eligcrit)[['state_fips', 
                                      'EligMinWorkHours', 
                                      'EligMinHoursAmount', 
                                      'EligMinHoursAmount_NOTES']]

#Now I want to create a new column with text, interpreting the other two columns
#From codebook: 
    #0 =  NA
    #1 = No minimum
    #2 = Yes, same minimum for all recipients
    #3 = Yes, different minimum for full-time and part-time care
    #92 = Not in manual


def min_hours_interpreter(row):
    """Interpret codes into weekly hours or text descriptions"""
    
    if row['EligMinWorkHours'] == 1:
        return('No minimum')
    elif row['EligMinWorkHours'] == 2 or row['EligMinWorkHours'] == 3 :
        if row['EligMinHoursAmount'] >= 0:
            return(row['EligMinHoursAmount'])
        elif row['EligMinHoursAmount'] == -5:
            return('Not in manual')
        elif row['EligMinHoursAmount'] == -3:
            return(row['EligMinHoursAmount_NOTES'])
        else:
            return('There is a problem here')
    else:
        return('There is a problem here') 

minhours['Interpretation'] = minhours.apply (lambda row: min_hours_interpreter(row), axis=1)
minhours = minhours[['state_fips', 'Interpretation']]

merge = minhours.merge(state_df, on='state_fips', how='outer')

merge


#plot

fig, ax = plt.subplots(figsize=(5,5))
ax = merge.plot(ax=ax, column='EligMinWorkHours', legend=True, alpha=0.25)
ax.axis('off')


#Income eligibility thresholds for family of 2
#whether a family with a CPS case is exempt from copayments


#Background checks of unlicensed home-based providers
#note that some states may appear to have no backchecks,
#but really they just have no unlicensed home-based providers





#If I were going to go forward, I'd get def of regions, 
#link to region shapefile, and then make chloropleth



#Other maps

#Sentiment analysis of governor speeches
#https://www.nasbo.org/mainsite/resources/stateofthestates/sos-summaries
#https://www.nasbo.org/resources/stateofthestates

#Abortion access

#Cost of childcare

#Measure of state progressiveness?

#Mean family income
#https://fred.stlouisfed.org/release/tables?eid=257197&rid=110

