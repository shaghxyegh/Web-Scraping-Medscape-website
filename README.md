# Web-Scraping-Medscape-website
Project Overview

This project is a web crawler designed to scrape data from Medscape, a comprehensive medical resource website. The crawler extracts information from various sections, including anatomy, drugs, simulations, and more. The scraped data is stored in both JSON and CSV formats for easy access and analysis.
Features
Crawled Sections: Extracts data from multiple sections of the Medscape website, such as anatomy, drugs, simulations, and other medical resources.
Data Formats: Saves scraped data in structured JSON and CSV formats for further processing or analysis.
Hierarchical Data Preservation: Maintains the nested structure of Medscape's categories and subcategories to ensure data integrity.
Challenges
Crawling the Medscape website presented several challenges:
Robot Restrictions: Medscape implements strict anti-bot measures, requiring careful handling to avoid being blocked.
Login Requirements: Some sections of the website are behind a login, necessitating authentication handling in the crawler.
Complex Website Structure: The website's nested structure and varying link patterns across sections required meticulous navigation to preserve the hierarchy of categories, subcategories, and other content.
Diverse Subdomains: Different sections of Medscape use distinct sublinks and structures, which demanded adaptive scraping logic.
