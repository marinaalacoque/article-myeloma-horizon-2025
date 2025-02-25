import pandas as pd
import json

#open main data
with open("./ctg-studies-myeloma-2003-to-2024.json", "r", encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

#filter geographic data
def get_geo_points(amostra):
    geoInfo = []
    locations = amostra["protocolSection"].get("contactsLocationsModule",{}).get("locations")
    id = amostra["protocolSection"]["identificationModule"]["nctId"]
    if not locations:
        return []
    for location in locations:
        if location.get("geoPoint"):
            geoInfo.append({
                "id": id,
                "facility": location.get("facility"),
                "latitude": location["geoPoint"]["lat"],
                "longitude": location["geoPoint"]["lon"]
            })
    return geoInfo

#filter relevant data for study

def get_study_data(amostra):
    return {
        "Id": amostra["protocolSection"]["identificationModule"]["nctId"],
        "lastUpdateSubmitDate": amostra["protocolSection"]["statusModule"]["lastUpdateSubmitDate"],
        "studyFirstSubmitDate": amostra["protocolSection"]["statusModule"]["studyFirstSubmitDate"],
        "endDate": amostra["protocolSection"]["statusModule"].get("completionDateStruct", {}).get("date"),
        "overallStatus": amostra["protocolSection"]["statusModule"]["overallStatus"],
        "phases": ", ".join(amostra["protocolSection"]["designModule"]["phases"]),
        "sendResult": True if amostra["protocolSection"]["statusModule"].get("resultsFirstSubmitDate") else False,
    }

study_data = []
for amostra in dados:
    study_data.append(get_study_data(amostra))

geo_data = []
for amostra in dados:
    geo_data.extend(get_geo_points(amostra))

df_study = pd.DataFrame(study_data)
df_study.to_csv("./ctg-studies-filtered.csv", index=False)

df_geo = pd.DataFrame(geo_data)
df_geo.to_csv("./ctg-geo-filtered.csv", index=False)