from urllib import request
import airflow.utils.dates
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

dag = DAG(
    dag_id="chapter4",
    start_date=airflow.utils.dates.days_ago(3),
    schedule_interval="@hourly",
    template_searchpath="/tmp",
)


# pageview download from wiki
def _get_data(year, month, day, hour, output_path):
    url = (
        "https://dumps.wikimedia.org/other/pageviews/"
        f"{year}/{year}-{month:0>2}/pageviews-{year}{month:0>2}{day:0>2}-{hour:0>2}0000.gz"
    )
    request.urlretrieve(url, output_path)


get_data = PythonOperator(
    task_id="get_data",
    python_callable=_get_data,
    op_kwargs={
        "year": "{{ execution_date.year }}",
        "month": "{{ execution_date.month }}",
        "day": "{{ execution_date.day }}",
        "hour": "{{ execution_date.hour }}",
        "output_path": "/tmp/wikipageviews.gz",
    },
    dag=dag,
)


# same bash version
# get_data = BashOperator(
#     task_id="get_data",
#     bash_command=(
#         "curl -o /tmp/wikipageviews.gz"
#         "https://dumps.wikimedia.org/other/pageviews"
#         "{{ execution_date.year }}/"
#         "{{ execution_date.year }}-"
#         "{{ '{:02}'.format(execution_date.month)}}"
#         "pageviwes-{{ execution_date.year }}"
#         "{{ '{:02}'.format(execution_date.month) }}"
#         "{{ '{:02}'.format(execution_date.day) }}-"
#         "{{ '{:02}'.format(execution_date.hour) }}0000.gz"
#     ),
#     dag=dag,
# )


# extract gzip
extract_gz = BashOperator(
    task_id="extract_gz", bash_command="gunzip --force /tmp/wikipageviews.gz", dag=dag
)


def _fetch_pageviews(pagenames, execution_date):
    result = dict.fromkeys(pagenames, 0)
    with open("/tmp/wikipageviews", "r") as f:
        for line in f:
            domain_code, page_title, view_counts, _ = line.split(" ")
            if domain_code == "en" and page_title in pagenames:
                result[page_title] = view_counts

    with open("/tmp/postgres_query.sql", "w") as f:
        for pagename, pageviewcount in result.items():
            f.write(
                "INSERT INTO pageview_counts VALUES ("
                f"'{pagename}', {pageviewcount}, '{execution_date}'"
                ");\n"
            )


fetch_pageviews = PythonOperator(
    task_id="fetch_pageveiws",
    python_callable=_fetch_pageviews,
    op_kwargs={"pagenames": {"Google", "Amazon", "Apple", "Microsoft", "Facebook"}},
    dag=dag,
)


write_to_postgres = PostgresOperator(
    task_id="write_to_postgres",
    postgres_conn_id="my_postgres",
    sql="postgres_query.sql",
    dag=dag,
)


get_data >> extract_gz >> fetch_pageviews >> write_to_postgres
