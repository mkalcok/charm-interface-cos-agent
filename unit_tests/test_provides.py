# Copyright 2025 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import charms_openstack.test_utils as test_utils

from src import provides


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = []
        hook_set = {
            "when": {
                "joined": ("endpoint.{endpoint_name}.joined",),
                "changed": ("endpoint.{endpoint_name}.changed",),
                "departed": ("endpoint.{endpoint_name}.departed",),
                "broken": ("endpoint.{endpoint_name}.broken",),
            },
        }
        # test that the hooks were registered
        self.registered_hooks_test_helper(provides, hook_set, defaults)


class _RelationMock(object):
    def __init__(self, relation_id="cos-agent:10", application_name=None, units=None):
        self.relation_id = relation_id
        self.to_publish_raw = {}
        self.to_publish = {}
        self.to_publish_app = {}
        self.application_name = application_name
        self.units = units


class TestCosAgentProvides(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_object(provides.hookenv, "application_name", return_value="myapp")
        self.patch_object(
            provides.hookenv,
            "model_uuid",
            return_value="47bfebeb-92ee-4cfa-b768-cd29749d33ac",
        )
        self.patch_object(provides.hookenv, "model_name", return_value="mymodel")
        self.patch_object(provides.hookenv, "local_unit", return_value="myapp/0")

        self.relation_mock = _RelationMock()

        self.ep_name = "cos-agent"
        self.ep = provides.CosAgentProvides(
            self.ep_name, [self.relation_mock.relation_id]
        )

        self.ep.relations[0] = self.relation_mock

    def test_update_cos_agent(self):
        self.maxDiff = None
        endpoint_index = 0
        expected_port = 9476
        expected_path = "/metrics"
        expected_host = "127.0.0.1"
        expected_job_name = "test_job"
        full_job_name = f"{self.ep.endpoint_name}_{endpoint_index}_{expected_job_name}"
        metric_endpoint = provides.MetricsEndpoint(
            port=expected_port,
            path=expected_path,
            host=expected_host,
            job_name=expected_job_name,
        )

        self.ep.update_cos_agent([metric_endpoint])
        expect_rel_data = {
            "dashboards": [],
            "log_alert_rules": {},
            "log_slots": [],
            "metrics_alert_rules": {},
            "metrics_scrape_jobs": [
                {
                    "job_name": f"{full_job_name}",
                    "metrics_path": f"{expected_path}",
                    "static_configs": [
                        {
                            "targets": [f"{expected_host}:{expected_port}"],
                        }
                    ],
                }
            ],
            "subordinate": None,
            "tracing_protocols": [],
        }

        relation_config_key = provides.CosAgentProviderUnitData.KEY
        self.assertEqual(
            self.relation_mock.to_publish.get(relation_config_key), expect_rel_data
        )
