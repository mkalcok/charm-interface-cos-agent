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

import inspect
from dataclasses import dataclass
from typing import Optional, List

from charms import reactive

from charmhelpers.core import hookenv

from .lib.cos_agent import CosAgentProviderUnitData


@dataclass
class MetricsEndpoint:
    port: int
    path: str = "/metrics"
    # cos-agent is an interface with a subordinate charm, therefore
    # localhost should be a sane default
    host: str = "localhost"
    job_name: str = "default"
    _job_prefix: str = ""

    @property
    def job_prefix(self):
        return self._job_prefix

    @job_prefix.setter
    def job_prefix(self, value):
        self._job_prefix = value

    def to_dict(self):
        return {
            "job_name": f"{self.job_prefix}{self.job_name}",
            "metrics_path": self.path,
            "static_configs": [{"targets": [f"{self.host}:{self.port}"]}],
        }


class CosAgentProvides(reactive.Endpoint):

    MetricsEndpoint = MetricsEndpoint

    @reactive.when("endpoint.{endpoint_name}.joined")
    def joined(self):
        hookenv.log(
            "{}: {} -> {}".format(
                self._endpoint_name,
                type(self).__name__,
                inspect.currentframe().f_code.co_name,
            ),
            level=hookenv.INFO,
        )
        reactive.set_flag(self.expand_name("{endpoint_name}.connected"))

    @reactive.when("endpoint.{endpoint_name}.changed")
    def changed(self):
        hookenv.log("COS Aent interface changed", level=hookenv.WARNING)
        reactive.set_flag(self.expand_name("{endpoint_name}.available"))

    @reactive.when("endpoint.{endpoint_name}.departed")
    def departed(self):
        reactive.clear_flag(self.expand_name("{endpoint_name}.connected"))
        reactive.clear_flag(self.expand_name("{endpoint_name}.available"))

    def update_cos_agent(
        self, metrics_endpoints: Optional[List[MetricsEndpoint]] = None
    ):
        metrics_endpoints = metrics_endpoints or []
        scrape_config = []
        for index, endpoint in enumerate(metrics_endpoints):
            endpoint.job_prefix = self.expand_name("{endpoint_name}_") + f"{index}_"
            scrape_config.append(endpoint.to_dict())
        hookenv.log(f"Updating scrape config: {scrape_config}", level=hookenv.DEBUG)

        data = CosAgentProviderUnitData(
            metrics_alert_rules={},
            log_alert_rules={},
            dashboards=[],
            metrics_scrape_jobs=scrape_config,
            log_slots=[],
            tracing_protocols=[],
        )

        for rel in self.relations:
            rel.to_publish[data.KEY] = data.model_dump()
