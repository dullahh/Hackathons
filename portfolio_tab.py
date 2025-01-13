import pymongo
from random import sample
import streamlit as st
import pandas as pd
from pulp import LpMaximize, LpProblem, LpVariable, LpStatus
import matplotlib.pyplot as plt

# MongoDB client setup (update your connection string)
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["investmentDB"]  # Database name
collection = db["synchronizedData"]  # Collection name for storing the data

# Custom exceptions
class NonFeasibleSolutionError(Exception):
    def __init__(self):
        pass

class InvalidInvestmentCloudParameterError(Exception):
    def __init__(self):
        pass

# InvestmentCloud class
class InvestmentCloud:
    def __init__(self, asset, expected_return, minimum, maximum):
        if minimum < 0 or minimum > maximum or maximum > 1:
            raise InvalidInvestmentCloudParameterError()

        self.asset = asset
        self.expected_return = expected_return
        self.minimum = minimum
        self.maximum = maximum

# AssetDist class to store asset distribution
class AssetDist:
    def __init__(self, name, proportion):
        self.name = name
        self.proportion = proportion

# Main render function
def render():
    st.header("Portfolio")

    # Placeholder for investment clouds (you can replace this with DB or user data)
    investment_clouds = [
        InvestmentCloud("S&P", 0.15, .10, .55),
        InvestmentCloud("Apple", 0.2, .11, .50),
        InvestmentCloud("Microsoft", 0.3, .05, .50),
        InvestmentCloud("Facebook", 0.1, .20, .60)
    ]

    selected_cloud = st.selectbox(
        "Select an Investment Cloud:",
        [cloud.asset for cloud in investment_clouds]
    )

    # Display information about the selected investment cloud
    selected_investment = next(cloud for cloud in investment_clouds if cloud.asset == selected_cloud)
    st.write(f"**Asset**: {selected_investment.asset}")
    st.write(f"**Expected Return**: {selected_investment.expected_return}")
    st.write(f"**Minimum Investment**: {selected_investment.minimum}")
    st.write(f"**Maximum Investment**: {selected_investment.maximum}")

    # Create DataFrame for displaying to the user
    table = {
        "Asset": [investment_cloud.asset for investment_cloud in investment_clouds],
        "Expected return": [investment_cloud.expected_return for investment_cloud in investment_clouds],
        "Minimum investment": [investment_cloud.minimum for investment_cloud in investment_clouds],
        "Maximum investment": [investment_cloud.maximum for investment_cloud in investment_clouds]
    }

    df = pd.DataFrame(table)

    # Create a container for the table and the buttons
    container = st.container()

    # Show the table
    with container:
        # Create two columns: one for the "Synchronize" button and one for the "Optimise Portfolio" button
        col1, col2 = st.columns([4, 1])  # 4: Table, 1: Synchronize button

        with col1:
            # Display the table
            st.dataframe(df)

        with col2:
            # Synchronize button placed on the right of the table
            if st.button("Synchronize"):
                synchronize_data(df)  # Pass the DataFrame directly

        # "Optimize Portfolio" button at the bottom
        if st.button("Optimise portfolio"):
            try:
                optimised_asset_dist = calculate_optimal_asset_dist(investment_clouds)
                display_assets_pie(optimised_asset_dist)
            except NonFeasibleSolutionError:
                st.error("Non feasible investment clouds")

# Synchronization logic - storing the current table to MongoDB
def synchronize_data(df):
    """
    This function stores the current table (investment cloud data) in MongoDB as dataToBeSent.
    """
    # Convert the DataFrame into a format suitable for MongoDB (list of dictionaries)
    data_to_be_sent = df.to_dict(orient="records")

    # Insert the data into the MongoDB collection
    collection.insert_one({"data": data_to_be_sent})
    
    st.write("Data has been synchronized with MongoDB.")  # Example message indicating synchronization

# Function to calculate optimal asset distribution using linear programming
def calculate_optimal_asset_dist(investment_clouds):
    model = LpProblem("Total expected return", LpMaximize)

    asset_dists = [LpVariable(investment_cloud.asset, lowBound=0) for investment_cloud in investment_clouds]
    model += sum(asset_dists[i] * investment_clouds[i].expected_return for i in range(len(investment_clouds)))

    for i in range(len(investment_clouds)):
        model += investment_clouds[i].minimum <= asset_dists[i]
        model += investment_clouds[i].maximum >= asset_dists[i]

    model += sum(asset_dist for asset_dist in asset_dists) == 1

    model.solve()

    if LpStatus[model.status] != "Optimal":
        raise NonFeasibleSolutionError()

    return [AssetDist(asset_dist.name, asset_dist.value()) for asset_dist in asset_dists]

# RGB color helper functions
def rgb_component(status):
    return "CC" if status else "33"

def is_white(r, g, b):
    return r == 1 and g == 1 and b == 1

def is_black(r, g, b):
    return r == 0 and g == 0 and b == 0

# Function to display pie chart for asset distribution
def display_assets_pie(assets):
    labels = [asset.name for asset in assets]
    proportions = [asset.proportion * 100 for asset in assets]
    rgb_binary_combinations = [(r, g, b) for b in [0, 1] for g in [0, 1] for r in [0, 1] if not is_white(r, g, b) and not is_black(r, g, b)]
    colors = [f"#{rgb_component(rgb[0])}{rgb_component(rgb[1])}{rgb_component(rgb[2])}" for rgb in rgb_binary_combinations]

    fig, ax = plt.subplots(figsize=(12, 10))  # Increase figure size explicitly (width=12, height=10)
    ax.pie(proportions, labels=labels, colors=colors, autopct="%1.1f%%", startangle=90, textprops={"color": "white"})
    fig.patch.set_facecolor("none")

    ax.axis("equal")

    st.pyplot(fig)

# Ensure that the render function is called when the script runs
if __name__ == "__main__":
    render()
