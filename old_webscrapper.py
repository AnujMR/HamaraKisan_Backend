import requests
from bs4 import BeautifulSoup
from pprint import pprint
from flask import jsonify
from old_store import commodity_map, state_map, districts
from datetime import datetime
from collections import defaultdict
import json
import os
def getTableData(state,district,commodity_name,startDate,endDate):
    stateCode=state_map[state]
    if district=="--Select--":
        districtCode=0
    else:
        districtCode = districts[stateCode][district]
    com_id = commodity_map[commodity_name]
    url = "https://www.agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity="+com_id+"&Tx_State=" + str(stateCode) + "&Tx_District="+str(districtCode)+"&Tx_Market=0&DateFrom=" + startDate + "&DateTo="+endDate+"&Fr_Date="+startDate+"&To_Date="+endDate+"&Tx_Trend=0&Tx_CommodityHead="+ commodity_name +"&Tx_StateHead="+ state +"&Tx_DistrictHead="+district+"&Tx_MarketHead=--Select--"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    print("Response status:", response.status_code)
    print("Response length:", len(response.text))
    print("HTML snippet:", response.text[:500])

    soup = BeautifulSoup(response.text, "html.parser")
    # pprint(soup.find("select", {"id":"ddlCommodity"}))
    data = []
    # The data table is usually inside <table id="cphBody_GridView1"> on this site
    table = soup.find("table", {"class": "tableagmark_new"})
    market_ids_element = soup.find("select", {"id": "ddlMarket"})
    market_ids = {opt.text.strip(): opt["value"] for opt in market_ids_element.find_all("option") if opt["value"] != "0"}
    # print(market_ids)
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
                    "min_price": int(float(cols[6])),
                    "max_price": int(float(cols[7])),
                    "modal_price": int(float(cols[8])),
                    "date": cols[9],
                    "variety":cols[4],
                    "market_id":market_ids[cols[2]]
                }   
                data.append(entry)
    return data

def getPriceTrend(state,district,market_id,startDate,endDate,comm):
    stateCode=state_map[state]
    districtCode = districts[stateCode][district]
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
                    # "market_name": cols[2],
                    # "district": cols[1],
                    # "state": state,
                    # "commodity": comm,
                    # "grade": cols[5],
                    "min_price": int(cols[6]),
                    "max_price": int(cols[7]),
                    "modal_price": int(cols[8]),
                    "date": cols[9],
                    # "variety":cols[4]
                }
                tabledata.append(entry)
        tabledata = sorted(tabledata,key=lambda x: datetime.strptime(x["date"], "%d %b %Y"))
    return tabledata

def getPriceTrendForDist(state,district,startDate,endDate,comm):
    stateCode=state_map[state]
    districtCode = districts[stateCode][district]
    com_id = commodity_map[comm]
    url = "https://www.agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity="+com_id+"&Tx_State=" + str(stateCode) + "&Tx_District="+str(districtCode)+"&Tx_Market=0&DateFrom=" + startDate + "&DateTo="+endDate+"&Fr_Date="+startDate+"&To_Date="+endDate+"&Tx_Trend=0&Tx_CommodityHead="+ comm +"&Tx_StateHead="+ state +"&Tx_DistrictHead="+district+"&Tx_MarketHead=--Select--"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"class": "tableagmark_new"})
    distTrend = defaultdict(list)
    if table:
        rows = table.find_all("tr")[1:]  
        for row in rows:
            cols = [col.get_text(strip=True) for col in row.find_all("td")]
            if len(cols) >= 7 and cols[0] != '-':
                entry = {
                    # "market_name": cols[2],
                    # "district": cols[1],
                    # "state": state,
                    # "commodity": comm,
                    # "grade": cols[5],
                    # "min_price": int(cols[6]),
                    # "max_price": int(cols[7]),
                    "modal_price": int(cols[8]),
                    "date": cols[9],
                    # "variety":cols[4]
                }
                distTrend[entry["date"]].append(entry["modal_price"])
        distTrend = {date: int(sum(prices)/len(prices)) for date, prices in distTrend.items()}
    return distTrend

def getTopDistrict(state,comm,startDate,endDate):
    stateCode=state_map[state]
    com_id = commodity_map[comm]
    url = "https://www.agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity="+com_id+"&Tx_State=" + str(stateCode) + "&Tx_District=0&Tx_Market=0&DateFrom=" + startDate + "&DateTo="+endDate+"&Fr_Date="+startDate+"&To_Date="+endDate+"&Tx_Trend=0&Tx_CommodityHead="+ comm+"&Tx_StateHead="+ state +"&Tx_DistrictHead=--Select&Tx_MarketHead=--Select--"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    # pprint(soup.find("select", {"id":"ddlCommodity"}))
    district_prices = defaultdict(list)

    table = soup.find("table", {"class": "tableagmark_new"})
    if table:
        rows = table.find_all("tr")[1:]  # skip header row
        for row in rows:
            cols = [col.get_text(strip=True) for col in row.find_all("td")]
            # print(cols)
            if len(cols) >= 7 and cols[0] != '-':
                entry = {
                    "district": cols[1],
                    "modal_price": int(cols[8])
                }
                district_prices[entry["district"]].append(entry["modal_price"])
    district_prices = {district: int(sum(prices)/len(prices)) for district, prices in district_prices.items()}
    sorted_top = sorted(district_prices.items(), key=lambda x: x[1], reverse=True)[:5]
    top_5_dict = dict(sorted_top)
    return top_5_dict

def getpinnedMandiComp(pinnedMandis,interested_Com,startDate,endDate):
    data={}
    for commodity_name in interested_Com:
        mandi_prices = {}
        # print(commodity_name)
        for mandi in pinnedMandis:
            # print(mandi)
            market_name=mandi["marketName"]
            state=mandi["state"]
            district=mandi["district"]
            mandi_id=mandi["id"]
            stateCode=state_map[state]
            districtCode=districts[stateCode][district]
            com_id=commodity_map[commodity_name]
            url = "https://www.agmarknet.gov.in/SearchCmmMkt.aspx?Tx_Commodity="+com_id+"&Tx_State=" + str(stateCode) + "&Tx_District="+str(districtCode)+"&Tx_Market="+str(mandi_id)+"&DateFrom=" + startDate + "&DateTo="+endDate+"&Fr_Date="+startDate+"&To_Date="+endDate+"&Tx_Trend=0&Tx_CommodityHead="+ commodity_name +"&Tx_StateHead="+ state +"&Tx_DistrictHead="+district+"&Tx_MarketHead="+market_name
            # print(url)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", {"class": "tableagmark_new"})
            if table:
                rows=table.find_all("tr")[1:]  
            model_prices=[]
            # print(rows)
            for row in rows:
                cols = [col.get_text(strip=True) for col in row.find_all("td")]
                if len(cols) >8 and cols[0] != '-':
                    model_prices.append(int(float(cols[8])))
            if len(model_prices)>0:
                average_price = sum(model_prices) / len(model_prices)
                mandi_prices[market_name]=(int)(average_price)
                data[commodity_name]=mandi_prices   
    return data
