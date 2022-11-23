
#Download the Urban Institute's manipulated U.S. shapefile
#from urbnmapr, which is only available for R

library(tidyverse)
library(urbnmapr)
library(sf)
setwd("~/Documents/GitHub/Data_Skills_2_project")

states_sf <- get_urbn_map("states", sf = TRUE)
st_write(states_sf, "UI_states.shp")
