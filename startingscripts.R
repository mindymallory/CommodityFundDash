library(XML)
library(RCurl)

library("methods")

# Convert the input xml file to a data frame.

xml.URL <- 'https://www.usda.gov/oce/commodity/wasde/latest.xml'
xmlfile <- getURL(xml.URL, ssl.verifyPeer=FALSE)
download.file(xml.URL, destfile='latestwasde.xml' <- tempfile(fileext=".xml"))
temp <- xmlTreeParse(latestwasde.xml)

xmldataframe <- xmlToDataFrame(temp)
print(xmldataframe)

# doesn't work but this stack overflow might hlep. 

https://stackoverflow.com/questions/31732680/parsing-xml-in-r-data-stored-in-attributes-with-blanks 
