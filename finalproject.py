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
pd.set_option('display.max_columns', None)

path = r'/Users/laurahatt/Documents/GitHub/Data_Skills_2_project'
CCDF = os.path.join(path, 'CCDF_databook.xlsx')
CCDF_full = pd.ExcelFile(CCDF)


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
def rate_calculator():
    
    ReimburseMultiplier = 1
    
    if ReimburseMultiplier == 1:
        print('monthly')
        pass
    elif ReimburseMultiplier > 1 and ReimburseMultiplier <= 5:
        print('weekly')
        pass
    elif ReimburseMultiplier > 5 and ReimburseMultiplier <= 30:
        print('daily')
        pass
    elif ReimburseMultiplier >30 and ReimburseMultiplier <= 240:
        print('hourly')
    else:
        print('what?')
    
    
rate_calculator()

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



#If I were going to go forward, I'd get def of regions, 
#link to region shapefile, and then make chloropleth


#



