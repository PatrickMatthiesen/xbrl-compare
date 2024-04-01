import requests
import json
import sys
import os
import csv
import datetime
import parse

cvrs = list(csv.reader(open("cvrNumbers.csv", "r"), delimiter=","))

previous_year = datetime.datetime.now().year - 2
this_year = datetime.datetime.now().year - 1

for cvr in cvrs:
    print(cvr[0])

    # Load the search query from the JSON file
    with open("searchQuery.json") as file:
        search_query = json.load(file)
        search_query["query"]["bool"]["must"][1] = { 'range': { 'offentliggoerelsesTidspunkt': { 'gte': str(previous_year+1) + '-01-01T00:00:00.000Z', 'lte': str(this_year+1) + '-12-31T23:59:59.999Z' } } }
        search_query["query"]["bool"]["must"].append({'term': {'cvrNummer': cvr[0]}})

    # Send the GET request to the ElasticSearch endpoint
    response = requests.get(
        "http://distribution.virk.dk/offentliggoerelser/_search", json=search_query
    )

    # Process the response
    if response.status_code == 200:
        # Do something with the search results
        results = response.json()

        # Print the results to file
        # with open("results.json", "w") as file:
        #     json.dump(results, file, indent=4)
        
        # # Get the last two years of financial reports
        hits = results["hits"]["hits"]

        if len(hits) != 2:
            print(cvr[0] + " does not have two reports")
            continue

        # Sort the hits based on offentliggoerelsesTidspunkt in ascending order
        sorted_hits = sorted(hits, key=lambda x: x["_source"]["regnskab"]["regnskabsperiode"]["startDato"])

        # Assign the oldest document to last_year and the other document to this_year
        previous_report = sorted_hits[0]
        latest_report = sorted_hits[1]
        
        previous_report_date = datetime.datetime.strptime(previous_report["_source"]["regnskab"]["regnskabsperiode"]["startDato"], '%Y-%m-%d')
        latest_report_date = datetime.datetime.strptime(latest_report["_source"]["regnskab"]["regnskabsperiode"]["startDato"], '%Y-%m-%d')
        
        if previous_report_date.year != previous_year:
            print(cvr[0] + " does not have a report from " + str(previous_year))
            exit(1)
            
        if latest_report_date.year != this_year:
            print(cvr[0] + " does not have a report from " + str(this_year))
            exit(1)
            
        # Get document URLs
        previous_report_url = None
        latest_report_url = None
        
        # Find the document URLs with application/xml mime type
        for document in previous_report["_source"]["dokumenter"]:
            if document["dokumentMimeType"] == "application/xml":
                previous_report_url = document["dokumentUrl"]
                break
        
        for document in latest_report["_source"]["dokumenter"]:
            if document["dokumentMimeType"] == "application/xml":
                latest_report_url = document["dokumentUrl"]
                break
        
        # Check if the URLs are found
        if previous_report_url is None:
            print(cvr[0] + " does not have a previous report with application/xml mime type")
            exit(1)
        
        if latest_report_url is None:
            print(cvr[0] + " does not have a latest report with application/xml mime type")
            exit(1)
            
        # Create a directory for storing the XBRL files
        xbrl_folder = os.path.join(os.path.expanduser("~/Desktop"), "xbrl_compare", "xbrl_files")
        os.makedirs(xbrl_folder, exist_ok=True)

        def download_report(filename, report_url, report_folder):
            report_path = os.path.join(report_folder, filename)
            response = requests.get(report_url)
            if response.status_code == 200:
                with open(report_path, "wb") as file:
                    file.write(response.content)
            else:
                print("Failed to download report:", response.status_code)
                print(response.text)
                exit(1)

        # Download the previous report
        previous_report_file = os.path.join(xbrl_folder, f"{cvr[0]}_{previous_year}.xml")
        download_report(previous_report_file, previous_report_url, xbrl_folder)

        # Download the latest report
        latest_report_file = os.path.join(xbrl_folder, f"{cvr[0]}_{this_year}.xml")
        download_report(latest_report_file, latest_report_url, xbrl_folder)
        
        # Parse the financial reports
        parse.parse(previous_report_file, latest_report_file)
    else:
        print("Error:", response.status_code)
        print(response.text)
