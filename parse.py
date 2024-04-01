import os
import sys
import pandas as pd
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element


def openAndParseXML(oldFile, nowFile):
    # Parse the XML document
    treeOld = ET.parse(oldFile)
    rootOld = treeOld.getroot()

    treeNow = ET.parse(nowFile)
    rootNow = treeNow.getroot()

    ns = {
        "xbrli": "http://www.xbrl.org/2003/instance",
        "fsa": "http://xbrl.dcca.dk/fsa",
    }

    # compare xbrli:identifier
    cvrNow = rootNow.find(".//xbrli:identifier", ns).text
    cvrOld = rootOld.find(".//xbrli:identifier", ns).text
    if cvrNow != cvrOld:
        print("CVR numbers do not match for")
        print(f"CVR in '{nowFile}' is {cvrNow}")
        print(f"CVR in '{oldFile}' is {cvrOld}")
        exit()

    print("cvr is:", cvrNow)
    return rootNow, rootOld, ns, cvrNow

# the names of the elements we want to extract
names = [
    "Revenue",
    "ExternalExpenses",
    "GrossResult",
    "DepreciationAmortisationExpenseAndImpairmentLossesOfPropertyPlantAndEquipmentAndIntangibleAssetsRecognisedInProfitOrLoss",
    "ProfitLossFromOrdinaryOperatingActivities",
    "OtherFinanceExpenses",
    "ProfitLossFromOrdinaryActivitiesBeforeTax",
    "TransferredToFromRetainedEarnings",
    "LandAndBuildings",
    "PropertyPlantAndEquipment",
    "NoncurrentAssets",
    "ShorttermTradeReceivables",
    "OtherShorttermReceivables",
    "ShorttermReceivables",
    "CashAndCashEquivalents",
    "CurrentAssets",
    "Assets",
    "ContributedCapital",
    "RetainedEarnings",
    "NoncurrentContractLiabilities",
    "LongtermLiabilitiesOtherThanProvisions",
    "ShorttermTradePayables",
    "ShorttermLiabilitiesOtherThanProvisions",
    "LiabilitiesOtherThanProvisions",
    "LiabilitiesAndEquity",
    # "ProfitLoss", # TODO: This occurs multiple times in the XML
    # "Equity", # TODO: This occurs multiple times in the XML
]


# Define a function to extract data from XML elements
def extract_data(element_old: Element, element_now: Element, ns: dict):
    data = []

    for name in names:
        old_value = int(element_old.find(f".//fsa:{name}", ns).text)
        now_value = int(element_now.findall(f"fsa:{name}", ns)[1].text)
        data.append({"name": name, "last year": old_value, "this year": now_value})

    return data


# data = extract_data(rootOld, rootNow)


def write_file(names, data, cvr):
    df = pd.DataFrame(data)

    # check that last year and this year are the same
    df["diff"] = df["this year"] - df["last year"]
    has_diff = df["diff"].any()
    if has_diff:
        print(cvr + " has_diff:", has_diff)

    status = "_FAILED" if has_diff else ""

    output_dir = os.path.join(
        os.path.expanduser("~/Desktop"), "xbrl_compare", "results"
    )
    os.makedirs(output_dir, exist_ok=True)

    writer = pd.ExcelWriter(
        f"{output_dir}/{cvr}_output{status}.xlsx", engine="xlsxwriter"
    )
    df.to_excel(writer, index=False, sheet_name="Sheet1")

    workbook = writer.book
    worksheet = writer.sheets["Sheet1"]
    numberFormat = workbook.add_format({"num_format": "#,###"})
    red_format = workbook.add_format({"bg_color": "red"})
    green_format = workbook.add_format({"bg_color": "green"})

    worksheet.set_column(0, 0, 40)
    worksheet.set_column(1, 2, 20, numberFormat)
    worksheet.conditional_format(
        f"B2:C{len(names)+1}",
        {"type": "formula", "criteria": "=$B2<>$C2", "format": red_format},
    )
    worksheet.conditional_format(
        f"B2:C{len(names)+1}",
        {"type": "formula", "criteria": "=$B2=$C2", "format": green_format},
    )

    writer.close()

# The main function to parse the XML files
def parse(last_year, this_year):
    now, old, ns, cvr = openAndParseXML(last_year, this_year)
    data = extract_data(old, now, ns)
    write_file(names, data, cvr)


if __name__ == "__main__":
    nowFile = sys.argv[1] if len(sys.argv) > 1 else "offentliggorelse.xml"
    oldFile = sys.argv[2] if len(sys.argv) > 2 else "offentliggorelse2022.xml"
    parse(oldFile, nowFile)
