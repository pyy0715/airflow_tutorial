# Summary

- DAG에서 테스크 의존성을 정의하는 방법을 확인합니다.
- 트리거 규칙을 사용하여, 조인을 구인하는 방법을 설명합니다.
- 트리거 규칙이 작업 실행에 주는 영향에 대한 기본 지식을 설명합니다.
- XCom을 이용하여 테스크 사이의 상태 공유 방법을 설명합니다.
- Airflow2의 Taskflow API를 사용해 파이썬 기반의 DAG을 단순화합니다.

## 기본 의존성 유형

1. 선형의존성 유형: 이전 테스크의 결과가 다음 테스크의 입력 값으로 사용되기 때문에 이동하기 전에 테스크를 완료해야만 합니다.
2. Fan-In/Fan-Out 의존성 유형: 테스크 간 복잡한 의존성 구조를 만들 수 있음
    - Fan-In(N:1), 하나의 테스크가 여러 업스트림 테스크에 영향을 받는 구조
    - Fan-Out(1:N), 한 테스크를 여러 다운스트림 테스크에 연결(브랜치 구조를 명확히 하기 위해 더미 테스크를 생성할 수도 있음)

## 브랜치하기

시스템 내 변경사항이 있더라도, 이전 시스템과 새로운 시스템 모두 정상 작동 필요

1. 테스크 내에서 브랜치: 테스크간의 차이점이 많지 않은 경우, 단일 테스크의 내부 브랜치를 통해 작업 가능하지만 특정 DAG 실행 중에 어떤 코드 분기를 사용하는지 알기 어려움
2. DAG 내부에서 브랜치: 두 개의 개별 테스크 세트를 개발하고, DAG가 이전 또는 새로운 시스템에서 작업을 실행할 수 있도록 선택

Airflow의 트리거 규칙에 의해 테스크  실행 시기를 제어합니다. 잘못된 트리거 규칙으로 브랜치를 결합하면, 이후의 모든 다운스트림 테스크는 건너뛰게 됩니다.
이를 위해 트리거 규칙을 `none failed`로 변경하면 모든 상위 항목이 실행 완료 및 실패가 없을 시에는 작업이 실행됩니다.

## 조건부 테스크

특정 조건에 따라 DAG에서 특정 테스크를 건너뛸 수 있는 방법이 있습니다.

1. 오퍼레이터 내부에서 실행 날짜를 명시적으로 체크한다. - 로직 조건이 혼용되며, UI에서 테스크 결과를 추적하는데 혼란스러울 수 있음
2. 테스크 자체를 조건부화 - 미리 정의된 조건에 따라서만 실행됨(e.g. LatestOnlyOperator)

## 트리거 규칙에 대한 추가정보

Airflow는 근본적으로 DAG를 실행할 때, 각 테스크를 지속적으로 확인하여 실행 여부를 확인합니다.

테스크 실행 시기를 결정하는 것이 트리거 규칙입니다. 기본 트리거 규칙은 `all_success`이며, 테스크를 실행하려면 모든 의존적인 테스크가 모두 성공적으로 완료되어야 함을 의미합니다. 반면에 `none failed` 트리거 규칙은 모든 업스트림 테스크가 실패없이 완료되었는지 여부만 확인합니다. 즉 성공 또는 스킵을 모두 허용하기 때문에 두 브랜치를 결합하기에 적절합니다.

DAG 실행 시작 순서

1. 의존성이 없는 시작 테스크를 실행하여 DAG 실행을 시작합니다.
2. 의존성 패턴에 따라 전체 DAG가 실행될 때까지 DAG의 나머지 테스크를 수행합니다.

## 테스크 간 데이터 공유

Airflow XCom을 사용하여 테스크 간에 작은 데이터를 공유할 수 있습니다. XCom은 기본적으로 테스크 간에 메세지를 교환하여 특정 상태를 공유할 수 있게 합니다.

### 사용 시 고려사항

- 명시적 의존성 테스크와 달리 DAG에 표시되지 않으며, 테스크 스케줄 시에도 고려되지 않음
- 오퍼레이터의 원자성을 무너뜨리는 패턴이 될 가능성이 있음
- XCom이 저장하는 모든 값은 직렬화를 지원해야 한다는 기술적 한계가 있음.

## Taskflow API로 파이썬 구현하기

XCom을 사용하여 테스크간에 데이터를 공유할 수 있지만, 상대적으로 많은 테스크 연결에 대해서 API로 구현할 시에는 번거로울 수 있습니다.
Airflow2부터는 Taskflow API를 제공하여 파이썬 테스크 및 의존성을 정의하기 위해 새로운 데코레이터 기반 API를 제공합니다.

데코레이터된 함수를 호출 시, 테스크를 위한 새로운 오퍼레이터 인스턴스를 반환합니다. 또한 함수의 return문에서 Airflow는 테스크에서 반환된 값을 XCom으로 자동 등록합니다.
이를 통해 의존성이 있는 함수에서 데코레이터를 선언하면 두 테스크간의 의존성을 확인하고, 두 테스크 간 XComs값을 전달하게 됩니다.

하지만 PythonOperator을 사용하여 구현되는 파이썬 테스크로 제한된다는 단점이 있습니다.