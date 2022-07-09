# Dashboard

With the dashboard, you can see how users interacted with the system.

## To Run

The DAYS_AGO environment variable determines how many days of worth logs (from today) are shown on the dashboard.

For example, DAYS_AGO=7 will only pull a week's worth of logs from the dynamo_db

- `DAYS_AGO=7 docker-compose up --build dashboard`