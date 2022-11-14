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

path = r'/Users/laurahatt/Documents/GitHub/Data_Skills_2_project'
CCDF = os.path.join(path, 'CCDF_databook.xlsx')
CCDF_full = pd.ExcelFile(CCDF)

#Current reimbursement rates in Washington State counties
reimburse = pd.read_excel(CCDF_full, 'ReimburseRates')
reimburse = reimburse[reimburse['State'] == 53]
reimburse = reimburse[reimburse['EndDat'] == '9999/12/31']
reimburse = reimburse[reimburse['ReimburseRatesProviderType'] == 'Level 1 child care centers']

reimburse[['State', 'County', 'ReimburseRatesProviderType', 'ReimburseDailyFull1']] 
#this is not enough regions for a good regression
