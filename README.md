# Oracle RAC Monitoring

## Standard Installation
This custom plugin is used to monitor Oracle RAC metrics from a 2-node RAC environment using Site24x7.

It connects to the configured RAC nodes, collects Oracle RAC metrics using `gv$` views, and sends them to the Site24x7 data center.

### Prerequisites
- Download and install the latest version of the Site24x7 Linux agent in the server where you plan to run the plugin.
- Python 3.7 or higher version should be installed.
- Install **oracledb** module for python

	```bash
	pip3 install oracledb
	```

- Roles need to be granted

	```sql
	grant create session to MONITOR_RAC;
	grant select_catalog_role to MONITOR_RAC;
	```

- If required in your RAC environment, grant explicit select access to the RAC performance views used by the plugin:

	```sql
	grant select on gv_$session to MONITOR_RAC;
	grant select on gv_$sysmetric to MONITOR_RAC;
	grant select on gv_$sysstat to MONITOR_RAC;
	grant select on gv_$system_event to MONITOR_RAC;
	grant select on gv_$lock to MONITOR_RAC;
	grant select on gv_$rowcache to MONITOR_RAC;
	grant select on gv_$active_instances to MONITOR_RAC;
	grant select on dba_users to MONITOR_RAC;
	```

### Installation

- Create a directory named `oracle_rac`.

	```bash
	mkdir oracle_rac
	cd oracle_rac/
	```

- Install the **oracledb** python module.

	```bash
	pip3 install oracledb
	```

- Place the below files under the `oracle_rac` directory:
	- `oracle_rac.py`
	- `oracle_rac.cfg`

- Make the script executable:

	```bash
	chmod +x oracle_rac.py
	```

- Execute the below command with appropriate arguments to check for valid JSON output for a single RAC node:

	```bash
	python3 oracle_rac.py --hostname "192.168.56.111" --port "1521" --sid "orcl.rac.local" --username "MONITOR_RAC" --password "PASSWORD" --oracle_home "/u01/app/oracle/product/19.0.0/dbhome_1/"
	```

- Execute the below command to validate the full RAC config:

	```bash
	python3 oracle_rac.py --config oracle_rac.cfg
	```

- After the above command gives the expected output, configure the relevant parameters in the `oracle_rac.cfg` file.

	```bash
	[global_configurations]
	use_agent_python = 1

	[RAC1]
	hostname = 192.168.56.111
	port = 1521
	sid = orcl.rac.local
	username = MONITOR_RAC
	password = PASSWORD
	tls = false
	oracle_home = /u01/app/oracle/product/19.0.0/dbhome_1/

	[RAC2]
	hostname = 192.168.56.112
	port = 1521
	sid = orcl.rac.local
	username = MONITOR_RAC
	password = PASSWORD
	tls = false
	oracle_home = /u01/app/oracle/product/19.0.0/dbhome_1/
	```

#### Linux

- Place the `oracle_rac` folder under the Site24x7 Linux Agent plugin directory:

	```bash
	mv oracle_rac /opt/site24x7/monagent/plugins
	```

The final path should be:

```bash
/opt/site24x7/monagent/plugins/oracle_rac/
```

The agent will automatically execute the plugin within five minutes and send performance data to the Site24x7 data center.

## Supported Metrics

### Database Activity Metrics

| Name | Description |
|-----|-------------|
| Oracle Active Nodes | Number of active RAC instances currently available in the cluster |
| Oracle Nodes Down | Number of RAC nodes down based on the expected cluster node count |
| Oracle Active Users | Number of active user sessions across RAC instances |
| Oracle Buffer Cache Hit Ratio | Percentage of data blocks served from buffer cache instead of disk |
| Oracle Dictionary Cache Hit Ratio | Ratio of dictionary cache hits across RAC nodes |
| Oracle Sort Ratio | Percentage of memory sorts compared to total sorts |
| Oracle Average Enqueue Timeouts | Total enqueue timeout occurrences across the RAC cluster |
| Oracle Long Queries Count | Number of currently active long-running queries |
| Oracle Long Queries Elapsed Time Sec | Maximum elapsed time in seconds among long-running queries |
| Oracle Database File IO Reads | Total physical reads across RAC instances |
| Oracle Database File IO Write Operations | Total physical writes across RAC instances |
| Oracle Redo Logs Contentions | Number of redo log space request contentions |
| Oracle User Locks | Number of TX locks in the RAC database |
| Oracle Locked Users | Number of locked database user accounts |

---

## Global Cache Metrics

| Name | Description |
|-----|-------------|
| Oracle GC CR Block Received Per Second | Number of consistent read blocks received per second through RAC global cache |
| Oracle GC Current Block Received Per Second | Number of current blocks received per second through RAC global cache |
| Oracle GC CR Blocks Served | Total number of consistent read blocks served |
| Oracle GC Current Blocks Served | Total number of current blocks served |
| Oracle GC CR Block Received Total | Total number of consistent read blocks received |
| Oracle GC Current Block Received Total | Total number of current blocks received |
| Oracle GC Average CR Get Time Ms | Average time taken to get consistent read blocks in milliseconds |
| Oracle GC Average Current Get Time Ms | Average time taken to get current blocks in milliseconds |
| Oracle Global Cache Blocks Lost | Number of global cache blocks lost over interconnect |
| Oracle Global Cache Blocks Corrupted | Number of corrupted global cache blocks detected |
| Oracle Global Cache Service Utilization | Combined total of GC CR and GC Current blocks received |
| Oracle Global Cache Average Block Receive Time Ms | Average block receive time derived from GC CR and GC Current get times |
| Oracle Global Cache Block Access Latency Ms | Average block access latency derived from GC request wait times |

---

## GC Wait Metrics

| Name | Description |
|-----|-------------|
| Oracle GC CR Request Avg Wait Ms | Average wait time for GC CR requests in milliseconds |
| Oracle GC CR Request Wait Count | Total number of GC CR request waits |
| Oracle GC Current Request Avg Wait Ms | Average wait time for GC Current requests in milliseconds |
| Oracle GC Current Request Wait Count | Total number of GC Current request waits |
| Oracle GC CR Block Busy Avg Wait Ms | Average wait time for busy GC CR blocks in milliseconds |
| Oracle GC CR Block Busy Wait Count | Total number of GC CR block busy waits |
| Oracle GC Current Block Busy Avg Wait Ms | Average wait time for busy GC Current blocks in milliseconds |
| Oracle GC Current Block Busy Wait Count | Total number of GC Current block busy waits |
| Oracle GC Buffer Busy Acquire Avg Wait Ms | Average wait time for GC buffer busy acquire events in milliseconds |
| Oracle GC Buffer Busy Acquire Wait Count | Total number of GC buffer busy acquire waits |
| Oracle GC Buffer Busy Release Avg Wait Ms | Average wait time for GC buffer busy release events in milliseconds |
| Oracle GC Buffer Busy Release Wait Count | Total number of GC buffer busy release waits |

---

## Interconnect and Cluster Metrics

| Name | Description |
|-----|-------------|
| Oracle Interconnect Bytes Received Per Second | Number of bytes received per second through RAC interconnect |
| Oracle Interconnect Bytes Sent Per Second | Number of bytes sent per second through RAC interconnect |
| Oracle Active Nodes | Count of active RAC nodes detected through `gv$active_instances` |
| Oracle Nodes Down | Count of RAC nodes unavailable compared with expected node count |

---

## Notes

- This plugin is designed for **Oracle RAC metrics only**.
- The script currently expects a **2-node RAC setup**.

The expected node count is controlled inside the Python script:

```python
EXPECTED_RAC_NODES = 2
```

If your RAC cluster size changes, update the above value in `oracle_rac.py`.

The plugin supports both:

- Single node CLI testing
- Multi-node config-based RAC monitoring

If `tls = true`, the plugin uses **TCPS connection with wallet location**.

If `tls = false`, the plugin uses the standard Oracle connection string format:

hostname:port/service_name


---

# Troubleshooting

If the plugin returns **Unable to read config file**, verify that `oracle_rac.cfg` exists in the same folder.

If the plugin returns **No RAC node sections found in oracle_rac.cfg**, ensure sections like:
---

[RAC1]
[RAC2]

are present.

If the plugin returns **All configured RAC nodes failed**, verify:

- Hostname/IP address
- Listener port
- Service name
- Username and password
- Oracle privileges
- Network connectivity between plugin host and RAC nodes

If the plugin returns Oracle client errors, verify:

```bash
oracle_home = /u01/app/oracle/product/19.0.0/dbhome_1/
```

If password contains special characters, keep it properly quoted during manual CLI testing.

---

# Example Commands

## Test RAC1

```bash
python3 oracle_rac.py \
--hostname "192.168.56.111" \
--port "1521" \
--sid "orcl.rac.local" \
--username "MONITOR_RAC" \
--password "PASSWORD" \
--oracle_home "/u01/app/oracle/product/19.0.0/dbhome_1/"
```

# Test RAC2

```bash
python3 oracle_rac.py \
--hostname "192.168.56.112" \
--port "1521" \
--sid "orcl.rac.local" \
--username "MONITOR_RAC" \
--password "PASSWORD" \
--oracle_home "/u01/app/oracle/product/19.0.0/dbhome_1/"
```

# Test Full RAC Configuration

```bash
python3 oracle_rac.py --config oracle_rac.cfg
```


You can paste this **directly into GitHub README.md** and it will render properly with:

- headings
- code blocks
- bullet lists
- command examples.