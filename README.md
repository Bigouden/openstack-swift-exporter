# OpenStack Swift Exporter

## Summary

Retrieve Objects From OpenStack Swift Container.

## Quick Start

```bash
DOCKER_BUILDKIT=1 docker build -t openstack-swift-exporter .
docker run -dit --name openstack-swift-exporter --env AUTH_TYPE=legacy --env ST_AUTH=http://<swift_url>:8080/auth/v1.0 --env ST_USER=test:tester --env ST_KEY=testing --env OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER=test openstack-swift-exporter
```

## Configuration

### Environment variables

| Environment Variable                            | Description                                                                                                        | Required                                         | Default                  |
|-------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|--------------------------|
| OPENSTACK_SWIFT_EXPORTER_NAME                   | Prometheus Exporter Name                                                                                           | no                                               | openstack-swift-exporter |
| OPENSTACK_SWIFT_EXPORTER_LOGLEVEL               | Prometheus Exporter Log Level                                                                                      | no                                               | INFO                     |
| OPENSTACK_SWIFT_EXPORTER_TZ                     | Prometheus Exporter Time Zone                                                                                      | no                                               | Europe/Paris             |
| OPENSTACK_SWIFT_EXPORTER_LIST_CONTAINER         | OpenStack Swift Container to list                                                                                  | yes                                              | None                     |
| OPENSTACK_SWIFT_EXPORTER_LIST_OPTIONS_DELIMITER | Listings only contain results up to the first instance of the delimiter in the object name                         | no                                               | None                     |
| OPENSTACK_SWIFT_EXPORTER_LIST_OPTIONS_PREFIX    | Only objects with the given prefix will be returned                                                                | no                                               | None                     |
| OPENSTACK_SWIFT_EXPORTER_PORT                   | Prometheus Exporter Port                                                                                           | no                                               | 8123                     |
| OPENSTACK_SWIFT_EXPORTER_RETRIES                | The number of times that the library should attempt to retry HTTP actions before giving up and reporting a failure | no                                               | 1                        |
| AUTH_TYPE                                       | OpenStack Auth Type : "legacy" or "keystone-v2" or "keystone-v3"                                                   | yes                                              | keystone-v3              |
| ST_AUTH                                         | OpenStack Auth URL                                                                                                 | yes for "legacy" auth type                       | None                     |
| ST_USER                                         | OpenStack User                                                                                                     | yes for "legacy" auth type                       | None                     |
| ST_KEY                                          | OpenStack Key                                                                                                      | yes for "legacy" auth type                       | None                     |
| OS_USERNAME                                     | OpenStack Username                                                                                                 | yes for "keystone-v2" or "keystone-v3" auth type | None                     |
| OS_PASSWORD                                     | OpenStack Password                                                                                                 | yes for "keystone-v2" or "keystone-v3" auth type | None                     |
| OS_TENANT_NAME                                  | OpenStack Tenant Name                                                                                              | yes for "keystone-v2" auth type                  | None                     |
| OS_AUTH_URL                                     | OpenStack Auth URL                                                                                                 | yes for "keystone-v2" or "keystone-v3" auth type | None                     |
| OS_PROJECT_NAME                                 | OpenStack Project Name                                                                                             | yes for "keystone-v3" auth type                  | None                     |
| OS_PROJECT_DOMAIN_NAME                          | OpenStack Project Domain Name                                                                                      | yes for "keystone-v3" auth type                  | None                     |

## Metrics

```bash
# HELP openstack_swift_object_bytes Openstack Swift Object Size in bytes.
# TYPE openstack_swift_object_bytes gauge
openstack_swift_object_bytes{container="test",name="test.txt",job="openstack-swift-exporter"} 4.0
# HELP openstack_swift_object_last_modified_total Openstack Swift Object Last Modified Datetime.
# TYPE openstack_swift_object_last_modified_total counter
openstack_swift_object_last_modified{container="test",name="test.txt",job="openstack-swift-exporter"} 1.70020871710237e+09
```
