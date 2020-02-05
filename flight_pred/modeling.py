import pickle

import pandas as pd
from prefect import task, context
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from config import PROJECT_HOME, TARGET_COLUMN, ID_COLUMN, DELAY_THRESHOLD


@task
def train_and_evaluate(flights: pd.DataFrame) -> pickle:
    logger = context.get("logger")

    X = flights.drop(columns=[TARGET_COLUMN, ID_COLUMN])
    y = flights[TARGET_COLUMN].map(lambda x: 1 if x > DELAY_THRESHOLD else 0)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)

    model = RandomForestClassifier(n_estimators=10, max_depth=10, n_jobs=-1, verbose=2, random_state=42)
    model.fit(X_train, y_train)
    pickle.dump(model, open(PROJECT_HOME / f'models/model_{DELAY_THRESHOLD}min.pkl', 'wb'))

    y_predicted = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_predicted.round())

    logger.info(f'Test accuracy: {accuracy}')

    return model


@task
def get_predictions(flights: pd.DataFrame) -> pd.DataFrame:
    model = pickle.load(open(PROJECT_HOME / 'models/model_15min.pkl', 'rb'))
    predictions = model.predict_proba(flights.drop(columns=[ID_COLUMN]))
    flights['prediction'] = [prediction[1] for prediction in predictions]
    return flights[[ID_COLUMN, 'prediction']]


@task
def add_predictions_to_flights_data(flights: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    flights_with_predictions = pd.merge(flights, predictions, how='left',
                                        left_on='identifiant', right_on='identifiant')
    return flights_with_predictions.sort_values(['date', 'depart_programme'], ascending=[False, False])


@task
def save_flights_with_predictions(flights_with_predictions: pd.DataFrame):
    flights_with_predictions.to_csv(PROJECT_HOME/'data/processed/predictions.csv', index=False)
