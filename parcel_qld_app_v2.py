import streamlit as st
import pandas as pd
import requests
import json
from io import BytesIO

### Layers Register SPP IMS ###
with open("layers_rep_IMS.txt", "r", encoding="utf-8") as f:
    data_list = json.load(f)
id_name_dict_IMS = {item["id"]: item["name"] for item in data_list}

### Layers Register SPP DAMS ###
with open("layers_rep_DAMS.txt", "r", encoding="utf-8") as f:
    data_list = json.load(f)
id_name_dict_DAMS = {item["id"]: item["name"] for item in data_list}


st.title("Queensland Planning Report Extractor")

# ---- Text input for parcel numbers ----
parcel_input = st.text_area(
    "Enter parcel numbers separated by commas (e.g., 2SP335900, 3SP335900, 1RP12345):",
    placeholder="2SP335900, 3SP335900"
)

def extract_field(parcel_number):
    url = "https://sppims-dams.dsdilgp.qld.gov.au/api/v1/lot_plan_geo/"
    payload = {"search_term_multiple": f"{parcel_number}"}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Origin": "https://sppims-dams.dsdilgp.qld.gov.au",
        "Referer": "https://sppims-dams.dsdilgp.qld.gov.au/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    data = response.json()

    return data["features"][0]["attributes"]


def extract_overlays(parcel_number):
    url = "https://sppims-dams.dsdilgp.qld.gov.au/api/v1/lot_plan_geo/"
    payload = {"search_term_multiple": f"{parcel_number}"}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Origin": "https://sppims-dams.dsdilgp.qld.gov.au",
        "Referer": "https://sppims-dams.dsdilgp.qld.gov.au/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-AU,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    data = response.json()
    data_geom = data["features"][0]["geometry"]

    # --- IMS layers ---
    url_layers_IMS = "https://sppims-dams.dsdilgp.qld.gov.au/api/v1/spp_intersect/"
    payload_layers = {"f": "json", "isEnvelope": False, "geometry": data_geom}

    resp_IMS = requests.post(url_layers_IMS, headers=headers, data=json.dumps(payload_layers))
    layer_list_IMS = resp_IMS.json().get("layerList", [])

    # --- DAMS layers ---
    url_layers_DAMS = "https://sppims-dams.dsdilgp.qld.gov.au/api/v1/dams_intersect/"
    resp_DAMS = requests.post(url_layers_DAMS, headers=headers, data=json.dumps(payload_layers))
    layer_list_DAMS = resp_DAMS.json().get("layerList", [])

    # --- Combine names ---
    layer_list_name = ""
    for layer_id in layer_list_IMS:
        layer_list_name += id_name_dict_IMS.get(int(layer_id), f"Unknown {layer_id}") + " / "
    for layer_id in layer_list_DAMS:
        layer_list_name += id_name_dict_DAMS.get(int(layer_id), f"Unknown {layer_id}") + " / "

    return layer_list_name.rstrip(" /")


# ---- Button to trigger extraction ----
if st.button("Extract Planning Data"):
    if parcel_input.strip():
        parcel_numbers = [p.strip() for p in parcel_input.split(",") if p.strip()]

        records = []
        for parcel_number in parcel_numbers:
            try:
                field_data = extract_field(parcel_number)
                entry = {
                    "Parcel Number": parcel_number,
                    "Lot Plan": field_data.get("LOT_PLAN", ""),
                    "Address": field_data.get("ADDRESS", ""),
                    "Suburb": field_data.get("LOCALITY", ""),
                    "LGA": field_data.get("LGA_NAME", ""),
                    "Area": field_data.get("LOT_AREA", ""),
                    "Tenure": field_data.get("TENURE", ""),
                    "Overlays": extract_overlays(parcel_number),
                }
                records.append(entry)
            except Exception as e:
                records.append({"Parcel Number": parcel_number, "Error": str(e)})

        df = pd.DataFrame(records)
        st.dataframe(df)

        # ---- Download Excel ----
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button(
            "💾 Download Excel",
            data=output.getvalue(),
            file_name="planning_extract.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.warning("Please enter at least one parcel number.")



