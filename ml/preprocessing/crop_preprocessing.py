import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler , LabelEncoder



df=pd.read_csv("data/Crop_recommendation.csv")


X=df.drop(columns="label")
y=df["label"]

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)



scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

label_encoder = LabelEncoder()

y_train_encoded = label_encoder.fit_transform(y_train)
y_test_encoded = label_encoder.transform(y_test)
