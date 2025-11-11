#!/usr/bin/env python3
import requests
import sys
import csv


def ask_question(base_url, question, csv_writer=None):
    print(f"\nQ: {question}")

    try:
        r = requests.post(f"{base_url}/query", json={"question": question})

        if r.status_code != 200:
            print(f"ERROR: {r.text}")
            if csv_writer:
                csv_writer.writerow([question, "ERROR", "", "", "", "", r.text])
            return False

        data = r.json()
        print(f"A: {data['value']} ({data['year_used']})")
        print(f"   {data['country']} | {data['indicator_code']}")

        if data.get('note'):
            print(f"   Note: {data['note']}")

        if csv_writer:
            csv_writer.writerow([
                question,
                data['value'],
                data['year_used'],
                data['country'],
                data['indicator_code'],
                data['indicator_name'],
                data.get('note', '')
            ])

        return True

    except Exception as e:
        print(f"EXCEPTION: {e}")
        if csv_writer:
            csv_writer.writerow([question, "EXCEPTION", "", "", "", "", str(e)])
        return False


def main():
    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"Testing API: {base_url}\n" + "=" * 50)

    questions = [
        "What is the GDP of Saudi Arabia in 2022?",
        "What is the population of females aged above 65 in Saudi Arabia in 2024?",
        "What is the GDP growth rate of Egypt in 2023?",
        "What is the total GDP of China in 2022?",
        "What was the GDP per capita for India in 2021?",
        "What is the population growth rate in India in 2022?",
        "What are the CO2 emissions per capita in Germany in 2020?",
        "What is the percentage of individuals using the internet in Brazil in 2021?",
        "What are the exports of goods and services in current USD for China in 2022?",
        "What are the imports as percentage of GDP for United States in 2021?",
        "What is the forest area as percentage of land area in Canada in 2020?",
        "What is the electric power consumption per capita in Norway in 2021?",
        "What is the labor force participation rate for females in Saudi Arabia in 2022?",
        "What is the agricultural land as percentage of total land area in Australia in 2021?",
        "What is the access to electricity in rural areas of Kenya in 2020?",
        "What is the central government debt as percentage of GDP for Japan in 2022?",
        "What is the arable land per person in Netherlands in 2021?",
        "What are the natural gas rents as percentage of GDP for Qatar in 2021?"
    ]

    csv_file = open('test_results.csv', 'w', newline='', encoding='utf-8')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Question', 'Value', 'Year', 'Country', 'Indicator Code', 'Indicator Name', 'Note'])

    passed = 0
    for q in questions:
        if ask_question(base_url, q, csv_writer):
            passed += 1

    csv_file.close()

    print(f"\n{'=' * 50}")
    print(f"Passed: {passed}/{len(questions)}")
    print(f"Results saved to test_results.csv")

    return 0 if passed == len(questions) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except requests.exceptions.ConnectionError:
        print(f"\nCan't connect to API. Is it running?")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped")
        sys.exit(1)
