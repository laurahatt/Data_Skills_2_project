
#Script to download the Urban Institute's manipulated U.S. shapefile
#from urbnmapr, which is only available for R

library(tidyverse)
library(urbnmapr)

states_sf <- get_urbn_map("states", sf = TRUE)

states_sf

states_sf %>% 
  ggplot(aes()) +
  geom_sf(fill = "grey", color = "#ffffff")