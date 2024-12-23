from fastapi import HTTPException, FastAPI
from db_utils import get_app_db_connection, get_security_db_connection, RealDictCursor
import json
from decimal import Decimal
import pandas as pd
import asyncio

app = FastAPI()

comparison_data ={
        "holdings": {
            "1398": {
                "account_number": "abc-123",
                "description": "Apple Inc.",
                "market_value": 1000.0,
                "weight": 0.1
            },
            "1639": {
                "account_number": "abc-123",
                "description": "Microsoft Corp.",
                "market_value": 1000.0,
                "weight": 0.1
            },
            "1388": {
                "account_number": "abc-123",
                "description": "Amazon.Com, Inc.",
                "market_value": 1000.0,
                "weight": 0.1
            },
            "1343": {
                "account_number": "abc-123",
                "description": "Tesla Inc",
                "market_value": 1000.0,
                "weight": 0.1
            },
            "1597": {
                "account_number": "abc-123",
                "description": "Johnson & Johnson",
                "market_value": 1000.0,
                "weight": 0.1
            },
            "394282": {
                "account_number": "abc-123",
                "description": "ProShares Ultra 7-10 Year Treasury",
                "market_value": 1000.0,
                "weight": 0.1
            },
            "2030": {
                "account_number": "abc-123",
                "description": "iShares iBoxx $ Invmt Grade Corp Bd ETF",
                "market_value": 1500.0,
                "weight": 0.15
            },
            "2033": {
                "account_number": "abc-123",
                "description": "iShares iBoxx $ High Yield Corp Bd ETF",
                "market_value": 1000.0,
                "weight": 0.1
            },
            "2333": {
                "account_number": "abc-123",
                "description": "iShares JP Morgan USD Em Mkts Bd ETF",
                "market_value": 500.0,
                "weight": 0.05
            },
            "1384": {
                "account_number": "abc-123",
                "description": "Alphabet Inc. Cap Stk CL A",
                "market_value": 1000.0,
                "weight": 0.1
            }
        }
    }

async def fetch_classification(security_ids: list):
            conn2 = get_security_db_connection()
            cursor2 = conn2.cursor(cursor_factory=RealDictCursor)
            sql = """
                SELECT 
                    s.security_id,
                    s.description,
                    s.isin,
                    s.sedol,
                    s.ticker,
                    ac.category_name AS allocation_category,
                    asc2.category_name AS allocation_sub_category,
                    it.instrument_type_name,
                    se.sector,
                    s.fund_category,
                    s.maturity,
                    fer.total_expense_ratio,
                    rad.commodity_beta,
                    rad.credit_beta,
                    rad.market_beta,
                    rad.rates_beta,
                    rad.size_beta,
                    rad.value_beta,
                    rad.alpha,
                    rad.total_vol,
                    rad.systematic_vol,
                    rad.idiosyncratic_vol,
                    fipd.yield_to_worst,
                    fipd.rate_duration,
                    fipd.spread_duration,
                    fipd.credit_spread,
                    fipd.security_coupon
                FROM
                    (SELECT * FROM sm.security WHERE security_id IN %s) AS s
                LEFT JOIN sm.sector se 
                    ON s.sector_id = se.sector_id
                LEFT JOIN sm.allocation_category_pair acp 
                    ON s.allocation_category_id = acp.allocation_category_pair_id
                LEFT JOIN sm.allocation_category ac 
                    ON acp.allocation_category_id = ac.allocation_category_id
                LEFT JOIN sm.allocation_sub_category asc2 
                    ON acp.allocation_sub_category_id = asc2.allocation_sub_category_id
                LEFT JOIN sm.instrument_type it 
                    ON s.instrument_type_id = it.instrument_type_id
                LEFT JOIN sm.fund_expense_ratio fer 
                    ON s.security_id = fer.security_id
                LEFT JOIN (
                    SELECT *
                    FROM (
                        SELECT *, 
                            RANK() OVER(PARTITION BY security_id ORDER BY end_date DESC) AS rn
                        FROM sm.risk_application_data
                        WHERE security_id IN %s
                    ) x
                    WHERE rn = 1
                ) rad 
                    ON s.security_id = rad.security_id
                LEFT JOIN (
                    SELECT *
                    FROM (
                        SELECT *, 
                            RANK() OVER(PARTITION BY security_id ORDER BY ref_date DESC) AS rn
                        FROM sm.fixed_income_pricing_data
                        WHERE security_id IN %s
                    ) y
                    WHERE rn = 1
                ) fipd 
                    ON s.security_id = fipd.security_id;
            """
            cursor2.execute(sql, (tuple(security_ids), tuple(security_ids), tuple(security_ids)))
            classification_data = cursor2.fetchall()
            conn2.close()
            return classification_data


async def fetch_market(security_ids: list):
            conn2 = get_security_db_connection()
            cursor2 = conn2.cursor(cursor_factory=RealDictCursor)
            sql2 = """
                SELECT * FROM   
                (SELECT security_id, description FROM sm.security WHERE security_id IN %s) AS s
                JOIN 
                (SELECT security_id, close_price AS price
                FROM (
                    SELECT *, 
                        RANK() OVER(PARTITION BY security_id ORDER BY ref_date DESC) AS rn
                    FROM sm.equity_pricing_data epd 
                    WHERE security_id IN %s
                ) y
                WHERE rn = 1) t ON s.security_id = t.security_id;
            """
            cursor2.execute(sql2, (tuple(security_ids), tuple(security_ids)))
            market = cursor2.fetchall()
            conn2.close()
            return market

@app.get("/fetch_data/{report_id}")
async def fetch_data(report_id: int):
    try:
        # Fetch `security_ids` from the first query
        conn = get_app_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT ipan.account_number, 
                jsonb_array_elements(ipah.tax_lots_recognized::jsonb -> 'security_id') AS security_id,
                jsonb_array_elements(ipah.tax_lots_recognized::jsonb -> 'quantity') AS quantity
            FROM app.investor_profile_account_holding ipah
            JOIN app.investor_profile_account_new ipan 
            ON ipah.investor_profile_account_id = ipan.investor_profile_account_id
            JOIN app.report_request rr 
            ON ipan.investor_profile_id = rr.investor_profile_id
            WHERE rr.report_request_id = %s
        """, (report_id,))
        securties = cursor.fetchall()
        conn.close()

        # Extract `security_ids`
        security_ids = [row["security_id"] for row in securties]


        # Run queries in parallel
        classification, market = await asyncio.gather(fetch_classification(security_ids), fetch_market(security_ids))

        # Process `classification`
        classification_data = {}
        for row in classification:
            security_id = row.pop('security_id')
            classification_data[security_id] = {
                key: (float(value) if isinstance(value, Decimal) else value)
                for key, value in row.items()
            }

        # Process `data_1` and `data_3`
        securities_df = pd.DataFrame(securties)
        market_df = pd.DataFrame(market)
        holdings_df = pd.merge(securities_df, market_df, on='security_id')
        holdings_df['price'] = holdings_df['price'].astype(float)
        holdings_df['market_value'] = holdings_df['quantity'] * holdings_df['price']
        total_market_value = holdings_df['market_value'].sum()
        holdings_df['weight'] = holdings_df['market_value'] / total_market_value

        holdings = {}
        for data in holdings_df.to_dict(orient='records'):
            security_id = str(data['security_id'])
            holdings[security_id] = {
                "account_number": data['account_number'],
                "description": data['description'],
                "market_value": round(data['market_value'], 2),
                "weight": round(data['weight'], 2),
            }

        # Final JSON structure
        holdings_json = {"left_side": {"holdings": holdings}, "right_side": comparison_data}

        # Save JSON files
        # with open("holdings.json", "w") as f:
        #     json.dump(holdings_json, f, indent=4)

        # with open("classification.json", "w") as f:
        #     json.dump(classification_data, f, indent=4)

        return classification_data, holdings_json

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     result = asyncio.run(fetch_data(report_id=6170))
#     print(result)