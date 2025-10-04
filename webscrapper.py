import requests
from bs4 import BeautifulSoup
from pprint import pprint
from flask import jsonify
from store import commodity_map, state_map, districts

def getTableData(state,district,commodity_name,startDate,endDate):

    stateCode=state_map[state]
    districtCode = districts[stateCode][district]
    com_id = commodity_map[commodity_name]

    url = "https://www.agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity="+com_id+"&Tx_State=" + str(stateCode) + "&Tx_District="+str(districtCode)+"&Tx_Market=0&DateFrom=" + startDate + "&DateTo="+endDate+"&Fr_Date="+startDate+"&To_Date="+endDate+"&Tx_Trend=0&Tx_CommodityHead="+ commodity_name +"&Tx_StateHead="+ state +"&Tx_DistrictHead="+district+"&Tx_MarketHead=--Select--"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    # pprint(soup.find("select", {"id":"ddlCommodity"}))
    data = []

    # The data table is usually inside <table id="cphBody_GridView1"> on this site
    table = soup.find("table", {"class": "tableagmark_new"})
    market_ids_element = soup.find("select", {"id": "ddlMarket"})
    market_ids = {opt.text.strip(): opt["value"] for opt in market_ids_element.find_all("option") if opt["value"] != "0"}
    print(market_ids)

    # print(table)
    if table:
        rows = table.find_all("tr")[1:]  # skip header row
        for row in rows:
            cols = [col.get_text(strip=True) for col in row.find_all("td")]
            # print(cols)
            if len(cols) >= 7 and cols[0] != '-':
                entry = {
                    "market_name": cols[2],
                    "district": cols[1],
                    "state": state,
                    "commodity": commodity_name,
                    "grade": cols[5],
                    "min_price": int(cols[6]),
                    "max_price": int(cols[7]),
                    "modal_price": int(cols[8]),
                    "date": cols[9],
                    "variety":cols[4]
                }
                data.append(entry)
    return {"data":data,"market_ids":market_ids}

def getData(state,district,market_id,intCom,startDate,endDate):

    data=[]
    stateCode=state_map[state]
    districtCode = districts[stateCode][district]
    for comm in intCom:
        com_id = commodity_map[comm]
        url = "https://www.agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity="+com_id+"&Tx_State=" + str(stateCode) + "&Tx_District="+str(districtCode)+"&Tx_Market="+str(market_id)+"&DateFrom=" + startDate + "&DateTo="+endDate+"&Fr_Date="+startDate+"&To_Date="+endDate+"&Tx_Trend=0&Tx_CommodityHead="+ comm +"&Tx_StateHead="+ state +"&Tx_DistrictHead="+district+"&Tx_MarketHead=--Select--"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        tabledata = []
        table = soup.find("table", {"class": "tableagmark_new"})
        if table:
            rows = table.find_all("tr")[1:]  
            for row in rows:
                cols = [col.get_text(strip=True) for col in row.find_all("td")]
                if len(cols) >= 7 and cols[0] != '-':
                    entry = {
                        "market_name": cols[2],
                        "district": cols[1],
                        "state": state,
                        "commodity": comm,
                        "grade": cols[5],
                        "min_price": int(cols[6]),
                        "max_price": int(cols[7]),
                        "modal_price": int(cols[8]),
                        "date": cols[9],
                        "variety":cols[4]
                    }
                    tabledata.append(entry)
        data.append(tabledata)
    return data