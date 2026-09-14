import os
import random
import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

brands = ['Maruti', 'Hyundai', 'Mahindra', 'Tata', 'Ford', 'Honda', 'Renault', 'Kia', 'Volkswagen', 'Skoda']
models = {
    'Maruti': ['Swift', 'Baleno', 'Brezza', 'Dzire'],
    'Hyundai': ['i20', 'Creta', 'Verna', 'Venue'],
    'Mahindra': ['Scorpio', 'XUV300', 'Thar', 'Bolero'],
    'Tata': ['Nexon', 'Safari', 'Harrier', 'Tiago'],
    'Ford': ['EcoSport', 'Freestyle', 'Endeavour'],
    'Honda': ['City', 'Amaze', 'Civic'],
    'Renault': ['Kwid', 'Triber', 'Duster'],
    'Kia': ['Seltos', 'Sonet'],
    'Volkswagen': ['Vento', 'Polo', 'Taigun'],
    'Skoda': ['Rapid', 'Octavia', 'Kushaq'],
}
fuel_types = ['Petrol', 'Diesel', 'CNG', 'LPG', 'Electric']
transmissions = ['Manual', 'Automatic']
owners = ['First', 'Second', 'Third', 'Fourth']

rows = []
for i in range(500):
    brand = random.choice(brands)
    car_model = random.choice(models[brand])
    year = random.choice([2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023])
    age = 2026 - year
    mileage = random.randint(10000, 120000)
    fuel = random.choice(fuel_types)
    transmission = random.choice(transmissions)
    owner = random.choice(owners)
    engine = random.randint(998, 2498)
    seats = random.choice([4, 5, 7])
    price_base = {
        'Petrol': 550000,
        'Diesel': 650000,
        'CNG': 420000,
        'LPG': 390000,
        'Electric': 820000,
    }[fuel]

    brand_bonus = {
        'Maruti': 100000,
        'Hyundai': 130000,
        'Mahindra': 140000,
        'Tata': 120000,
        'Ford': 110000,
        'Honda': 150000,
        'Renault': 90000,
        'Kia': 150000,
        'Volkswagen': 140000,
        'Skoda': 140000,
    }[brand]
    age_penalty = age * 40000
    mileage_penalty = mileage * 4
    fuel_multiplier = {
        'Petrol': 1.0,
        'Diesel': 1.12,
        'CNG': 0.84,
        'LPG': 0.78,
        'Electric': 1.3,
    }[fuel]
    transmission_bonus = 80000 if transmission == 'Automatic' else 0
    owner_penalty = {
        'First': 0,
        'Second': 25000,
        'Third': 50000,
        'Fourth': 80000,
    }[owner]
    engine_bonus = max(0, engine - 1200) * 25
    seats_bonus = max(0, seats - 4) * 25000

    price = price_base + brand_bonus + transmission_bonus + engine_bonus + seats_bonus
    price = price * fuel_multiplier - age_penalty - mileage_penalty - owner_penalty
    price += random.randint(-90000, 120000)
    price = max(price, 150000)

    rows.append({
        'name': f'{brand} {car_model} {year}',
        'year': year,
        'selling_price': round(price, 2),
        'km_driven': mileage,
        'fuel': fuel,
        'seller_type': 'Dealer' if random.random() > 0.2 else 'Individual',
        'transmission': transmission,
        'owner': owner,
        'mileage': round(random.uniform(10, 25), 2),
        'engine': engine,
        'max_power': round(random.uniform(50, 180), 2),
        'torque': f'{random.randint(20, 80)}Nm',
        'seats': seats,
    })

os.makedirs('data', exist_ok=True)
pd.DataFrame(rows).to_csv('data/car_data.csv', index=False)
print('Generated data/car_data.csv with', len(rows), 'rows.')
