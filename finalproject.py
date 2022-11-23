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

minhours = record_selector(eligcrit)[['state_fips', 'EndDat', 'EligMinWorkHours', 'EligMinHoursAmount']]
minhours


#issue with more states in minhours than in state_df
len(minhours)
len(state_df)

minhours.dtypes #int
state_df.dtypes #obj

minhours['state_fips']

state_df = state_df.astype({'state_fips':'int'})
merge = minhours.merge(state_df, on='state_fips', how='outer')

merge
#issues
#from minhours, 60, 66, 69, 72 and 78 don't have shapefiles
#60 is American Samoa, 66 is Guam, 69 is northern mariana islands,
#72 is PR, 78 is Virgin Islands
#I don't need any of these in my plots - states only

#from state_df, 13 and 30 don't have Urban data
#there's no open record for Georgia or Montana!


#plot

fig, ax = plt.subplots(figsize=(5,5))

from mpl_toolkits.axes_grid1 import make_axes_locatable
divider = make_axes_locatable(ax)
cax = divider.append_axes('right', size='5%', pad=0.1)

ax = merge.plot(ax=ax, cmap = 'OrRd', column='num_ADU_apps', 
                    legend=True, alpha=0.25, edgecolor='black', cax=cax)

ax.axis('off')
ax.set_title(f'{input.var()}, \n Chicago, by community area')


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

