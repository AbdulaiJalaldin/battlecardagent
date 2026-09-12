start agent
ingestion layer
1.takes information about the company via doc format or pdf and save to  db

web scraper agent
uses firecrawl to turn the website into a clean md for the llm 

(are we the ones going to give the agent the link to the competitors site or )

after the web scraping  it goes through the email to see any competitor related information (we use gmail api with read only access)

so we hash the scraped data section by section and store it in a db for each competitor we store the md maybe in a local directory or aws and only add the path of the md to the db so next time we scrape a new data, we hash it and compare to the old one if the same ,nothing happens. if different, we insert the  path to the new md file in the db  

after hashing and storing in the db with the path to the md ,we now give the md to the llm in sections becasue of context reason so we give the md to the llm and it extract the key information we need to display on the battle card i.e 
company name
company overview
pricing
product features


 and store it in a db again and it will use this information above and come up with 
strength
weakness
how to handle customer objection
and update the db for each competitor with this 
 so the streamlit can read it directly,so the llm does all the work in the background and when you open your site it just read directly from the db for fast loading  

 notion,click up ,coda ,aritable








 Homepage /	
	Product / Platform /product, /platform
	Solutions / Use Cases /solutions, /use-cases
	Pricing /pricing	
	Customers / Case Studies 
	Comparison pages /compare
	Features /features
about