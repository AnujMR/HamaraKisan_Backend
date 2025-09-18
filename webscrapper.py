import requests
from bs4 import BeautifulSoup
from pprint import pprint
from store import commodity_map, state_map, districts
from flask import jsonify


def getTableData():

    state="Madhya Pradesh"
    stateCode=state_map[state]
    district = "Khandwa"
    districtCode = districts[stateCode][district]
    commodity_name="Tomato"
    com_id = commodity_map[commodity_name]
    startDate="01-Sep-2025"
    endData="03-Sep-2025"


    url = "https://www.agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity="+com_id+"&Tx_State=" + str(stateCode) + "&Tx_District="+str(districtCode)+"&Tx_Market=0&DateFrom=" + startDate + "&DateTo="+endData+"&Fr_Date="+startDate+"&To_Date="+endData+"&Tx_Trend=0&Tx_CommodityHead="+ commodity_name +"&Tx_StateHead="+ state +"&Tx_DistrictHead="+district+"&Tx_MarketHead=--Select--"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    # pprint(soup.find("select", {"id":"ddlCommodity"}))
    data = []

    # The data table is usually inside <table id="cphBody_GridView1"> on this site
    table = soup.find("table", {"class": "tableagmark_new"})
    # print(table)
    if table:
        rows = table.find_all("tr")[1:]  # skip header row
        for row in rows:
            cols = [col.get_text(strip=True) for col in row.find_all("td")]
            if len(cols) >= 7 and cols[0] != '-':
                entry = {
                    "market_name": cols[2],
                    "district": cols[1],
                    "state": cols[0],
                    "commodity": commodity_name,
                    "grade": cols[5],
                    "min_price": int(cols[6]),
                    "max_price": int(cols[7]),
                    "modal_price": int(cols[8]),
                    "date": cols[9]
                }
                data.append(entry)

    # print scraped data
    arr=[]
    for item in data:
        arr.append(item)
    print(arr)
    return {"data" : arr}

getTableData()