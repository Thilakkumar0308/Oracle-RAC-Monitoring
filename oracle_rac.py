#!/usr/bin/python3
import json
import os
import warnings
warnings.filterwarnings("ignore")

PLUGIN_VERSION = 1
HEARTBEAT = True

METRICS_UNITS = {
    # Global Cache / Interconnect
    "GC CR Block Received Per Second": "count",
    "GC Current Block Received Per Second": "count",
    "GC Average CR Get Time": "ms",
    "GC Average Current Get Time": "ms",
    "Global Cache Blocks Lost": "count",
    "Global Cache Blocks Corrupted": "count",
    "GC CR Blocks Served Per Second": "count",
    "GC Current Blocks Served Per Second": "count",
    "GC CR Block Received Total": "count",
    "GC Current Block Received Total": "count",
    "GC CR Request Avg Wait Time": "ms",
    "GC Current Request Avg Wait Time": "ms",
    "GC CR Block Busy Avg Wait Time": "ms",
    "GC Current Block Busy Avg Wait Time": "ms",
    "GC Buffer Busy Acquire Avg Wait Time": "ms",
    "GC Buffer Busy Release Avg Wait Time": "ms",
    "GC CR Request Wait Count": "count",
    "GC Current Request Wait Count": "count",
    "GC CR Block Busy Wait Count": "count",
    "GC Current Block Busy Wait Count": "count",
    "GC Buffer Busy Acquire Wait Count": "count",
    "GC Buffer Busy Release Wait Count": "count",
    "Interconnect Bytes Received Per Second": "bytes",
    "Interconnect Bytes Sent Per Second": "bytes",
    # Session / User Activity
    "Active Users": "count",
    "Buffer Cache Hit Ratio": "%",
    "Dictionary Cache Hit Ratio": "%",
    "Average Enqueue Timeouts": "count",
    "Long Queries Count": "count",
    "Long Queries Elapsed Time": "sec",
    # I/O
    "Database File IO Reads": "count",
    "Database File IO Write Operations": "count",
    "Redo Log Contentions": "count",
    # Locks
    "User Locks": "count",
    "Locked Users": "count",
    # RAC Node Health
    "Active RAC Nodes": "count",
    "RAC Nodes Down": "count",
    # Performance Ratios
    "Sort Ratio": "%",
    "Global Cache Service Utilization": "count",
    "Global Cache Average Block Receive Time": "ms",
    "Global Cache Block Access Latency": "ms",
    # Tablespace / PDB / ASM nested units
    "Tablespace_Details": {
        "Tablespace_Size": "mb",
        "Used_Percent": "%",
        "Used_Space": "mb"
    },
    "Tablespace_Datafile_Details": {
        "Data_File_Size": "mb",
        "Max_Data_File_Size": "mb",
        "Usable_Data_File_Size": "mb"
    },
    "PDB_Details": {
        "PDB_Size": "mb"
    },
    "ASM_Details": {
        "total_gb": "GB",
        "free_gb": "GB",
        "pct_free": "%"
    },
    "RAC_Node_Details": {
        "Host_Name": "",
        "Status": "",
        "Instance_Number": "count"
    }
}


class oracle:

    def __init__(self, args):
        self.maindata = {}
        self.maindata['plugin_version'] = PLUGIN_VERSION
        self.maindata['heartbeat_required'] = HEARTBEAT
        self.maindata['units'] = METRICS_UNITS
        self.username = args.username
        self.password = args.password
        self.sid = args.sid
        self.hostname = args.hostname
        self.port = args.port
        self.tls = args.tls.lower()
        self.wallet_location = args.wallet_location
        self.oracle_home = args.oracle_home

    def connect(self, dsn):
        try:
            import oracledb
            if self.oracle_home and self.oracle_home != "None" and os.path.exists(self.oracle_home):
                try:
                    oracledb.init_oracle_client(lib_dir=self.oracle_home)
                except Exception:
                    pass
            self.conn = oracledb.connect(user=self.username, password=self.password, dsn=dsn)
            self.c = self.conn.cursor()
            return (True, "Connected")
        except Exception as e:
            self.conn = None
            self.c = None
            return (False, str(e))

    def close_connection(self):
        try:
            if hasattr(self, 'c') and self.c:
                self.c.close()
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
        except Exception:
            pass

    def execute_query_row_col(self, query, col_change=False):
        queried_data = {}
        try:
            self.c.execute(query)
            col_names = [row[0] for row in self.c.description]
            tot_cols = len(col_names)
            if col_change:
                for row in self.c:
                    for i in range(tot_cols):
                        queried_data[str.title(col_names[i])] = row[i]
                    break
            else:
                for row in self.c:
                    for i in range(tot_cols):
                        queried_data[col_names[i]] = row[i]
                    break
        except Exception as e:
            queried_data["status"] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_sysmetric_bulk(self):
        """
        Fetch RAC-level GV$SYSMETRIC metrics that map directly to named RAC metrics.
        Uses GV$SYSMETRIC (all instances) and averages/sums across instances where needed.
        """
        queried_data = {}
        # These metric names are the exact strings Oracle uses in GV$SYSMETRIC
        sysmetric_map = {
            "GC CR Block Received Per Second": "GC CR Block Received Per Second",
            "GC Current Block Received Per Second": "GC Current Block Received Per Second",
            "GC Average CR Get Time": "GC Average CR Get Time",
            "GC Average Current Get Time": "GC Average Current Get Time",
            "Global Cache Blocks Lost": "Global Cache Blocks Lost",
            "Global Cache Blocks Corrupted": "Global Cache Blocks Corrupted",
            "GC CR Blocks Served Per Second": "GC CR Blocks Served Per Second",
            "GC Current Blocks Served Per Second": "GC Current Blocks Served Per Second",
            "Buffer Cache Hit Ratio": "Buffer Cache Hit Ratio",
        }
        metric_list = "','".join(sysmetric_map.keys())
        query = f"""
            SELECT METRIC_NAME, AVG(VALUE)
            FROM GV$SYSMETRIC
            WHERE METRIC_NAME IN ('{metric_list}')
            GROUP BY METRIC_NAME
        """
        try:
            self.c.execute(query)
            for row in self.c:
                metric_name, value = row
                if metric_name in sysmetric_map:
                    queried_data[sysmetric_map[metric_name]] = round(float(value), 4) if value is not None else 0
        except Exception as e:
            queried_data['status'] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_sysstat_bulk(self):
        """
        Fetch cumulative stats from GV$SYSSTAT (summed across all RAC instances).
        """
        queried_data = {}
        # Oracle stat names -> our metric names
        sysstat_map = {
            "gc cr blocks received":          "GC CR Block Received Total",
            "gc current blocks received":     "GC Current Block Received Total",
            "gc cr blocks served":            "GC CR Blocks Served Per Second",   # fallback raw
            "gc current blocks served":       "GC Current Blocks Served Per Second",
            "physical reads":                 "Database File IO Reads",
            "physical writes":                "Database File IO Write Operations",
            "redo log space requests":        "Redo Log Contentions",
            "sorts (disk)":                   "_sorts_disk",
            "sorts (memory)":                 "_sorts_memory",
            "sorts (rows)":                   "_sorts_rows",
        }
        stat_list = "','".join(sysstat_map.keys())
        query = f"""
            SELECT LOWER(n.name), SUM(s.value)
            FROM GV$SYSSTAT s
            JOIN GV$STATNAME n ON s.statistic# = n.statistic# AND s.inst_id = n.inst_id
            WHERE LOWER(n.name) IN ('{stat_list}')
            GROUP BY LOWER(n.name)
        """
        try:
            self.c.execute(query)
            raw = {}
            for row in self.c:
                stat_name, value = row
                raw[stat_name] = value if value is not None else 0

            for oracle_name, metric_name in sysstat_map.items():
                if oracle_name in raw and not metric_name.startswith("_"):
                    queried_data[metric_name] = raw[oracle_name]

            # Sort Ratio = sorts(memory) / (sorts(memory) + sorts(disk)) * 100
            sorts_mem = raw.get("sorts (memory)", 0)
            sorts_disk = raw.get("sorts (disk)", 0)
            total_sorts = sorts_mem + sorts_disk
            queried_data["Sort Ratio"] = round((sorts_mem / total_sorts) * 100, 2) if total_sorts > 0 else 0

        except Exception as e:
            queried_data['status'] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_gc_wait_metrics(self):
        """
        Derive GC wait time and count metrics from GV$SYSTEM_EVENT.
        Covers: GC CR/Current request, busy, and buffer busy waits.
        """
        queried_data = {}
        # Oracle event name -> (avg_wait_metric, wait_count_metric)
        event_map = {
            "gc cr request":            ("GC CR Request Avg Wait Time",          "GC CR Request Wait Count"),
            "gc current request":       ("GC Current Request Avg Wait Time",     "GC Current Request Wait Count"),
            "gc cr block busy":         ("GC CR Block Busy Avg Wait Time",       "GC CR Block Busy Wait Count"),
            "gc current block busy":    ("GC Current Block Busy Avg Wait Time",  "GC Current Block Busy Wait Count"),
            "gc buffer busy acquire":   ("GC Buffer Busy Acquire Avg Wait Time", "GC Buffer Busy Acquire Wait Count"),
            "gc buffer busy release":   ("GC Buffer Busy Release Avg Wait Time", "GC Buffer Busy Release Wait Count"),
        }
        event_list = "','".join(event_map.keys())
        query = f"""
            SELECT LOWER(event), SUM(total_waits), SUM(time_waited_micro)/1000
            FROM GV$SYSTEM_EVENT
            WHERE LOWER(event) IN ('{event_list}')
            GROUP BY LOWER(event)
        """
        try:
            self.c.execute(query)
            for row in self.c:
                event_name, total_waits, time_waited_ms = row
                if event_name in event_map:
                    avg_metric, count_metric = event_map[event_name]
                    total_waits = total_waits or 0
                    time_waited_ms = float(time_waited_ms) if time_waited_ms else 0
                    avg_wait = round(time_waited_ms / total_waits, 4) if total_waits > 0 else 0
                    queried_data[avg_metric] = avg_wait
                    queried_data[count_metric] = total_waits
        except Exception as e:
            queried_data['status'] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_interconnect_metrics(self):
        """
        RAC interconnect traffic from GV$SYSSTAT.
        """
        queried_data = {}
        query = """
            SELECT LOWER(n.name), SUM(s.value)
            FROM GV$SYSSTAT s
            JOIN GV$STATNAME n ON s.statistic# = n.statistic# AND s.inst_id = n.inst_id
            WHERE LOWER(n.name) IN (
                'gc cr blocks received',
                'gc current blocks received',
                'gc cr blocks served',
                'gc current blocks served'
            )
            GROUP BY LOWER(n.name)
        """
        # Interconnect bytes come from GV$CLUSTER_INTERCONNECTS if available, else estimate
        interconnect_query = """
            SELECT
                SUM(RECEIVED) AS bytes_received,
                SUM(SENT) AS bytes_sent
            FROM GV$CLUSTER_INTERCONNECTS
        """
        try:
            self.c.execute(interconnect_query)
            for row in self.c:
                bytes_received, bytes_sent = row
                queried_data["Interconnect Bytes Received Per Second"] = bytes_received if bytes_received else 0
                queried_data["Interconnect Bytes Sent Per Second"] = bytes_sent if bytes_sent else 0
        except Exception:
            # GV$CLUSTER_INTERCONNECTS may not be available on all configs — fallback to 0
            queried_data["Interconnect Bytes Received Per Second"] = 0
            queried_data["Interconnect Bytes Sent Per Second"] = 0
        return queried_data

    def execute_session_metrics(self):
        """
        Active users, long queries, locks, locked users.
        """
        queried_data = {}
        queries = {
            "Active Users": """
                SELECT COUNT(DISTINCT username)
                FROM GV$SESSION
                WHERE status = 'ACTIVE' AND username IS NOT NULL
            """,
            "Long Queries Count": """
                SELECT COUNT(*)
                FROM GV$SESSION
                WHERE status = 'ACTIVE'
                  AND type <> 'BACKGROUND'
                  AND last_call_et > 60
            """,
            "Long Queries Elapsed Time": """
                SELECT NVL(SUM(last_call_et), 0)
                FROM GV$SESSION
                WHERE status = 'ACTIVE'
                  AND type <> 'BACKGROUND'
                  AND last_call_et > 60
            """,
            "User Locks": """
                SELECT COUNT(*)
                FROM GV$LOCK
                WHERE type = 'UL'
            """,
            "Locked Users": """
                SELECT COUNT(DISTINCT sid)
                FROM GV$SESSION
                WHERE blocking_session IS NOT NULL
            """,
            "Average Enqueue Timeouts": """
                SELECT NVL(ROUND(AVG(value), 2), 0)
                FROM GV$SYSSTAT
                WHERE LOWER(name) = 'enqueue timeouts'
            """,
        }
        for metric_name, query in queries.items():
            try:
                self.c.execute(query)
                for row in self.c:
                    queried_data[metric_name] = row[0] if row[0] is not None else 0
                    break
            except Exception as e:
                queried_data[metric_name] = 0
        return queried_data

    def execute_rac_node_metrics(self):
        """
        RAC node health: active nodes, nodes down, per-instance details.
        """
        queried_data = {}
        try:
            # Active and down nodes from GV$INSTANCE
            node_query = """
                SELECT
                    inst_id,
                    instance_name,
                    host_name,
                    status,
                    instance_number
                FROM GV$INSTANCE
                ORDER BY inst_id
            """
            self.c.execute(node_query)
            rows = self.c.fetchall()

            active = 0
            down = 0
            node_list = []
            for row in rows:
                inst_id, inst_name, host_name, status, inst_num = row
                node_dict = {
                    "name": inst_name,
                    "Instance_Number": inst_num,
                    "Host_Name": host_name,
                    "Status": status
                }
                node_list.append(node_dict)
                if status == "OPEN":
                    active += 1
                else:
                    down += 1

            queried_data["Active RAC Nodes"] = active
            queried_data["RAC Nodes Down"] = down
            queried_data["RAC_Node_Details"] = node_list

        except Exception as e:
            queried_data['status'] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_dictionary_cache_hit_ratio(self):
        queried_data = {}
        try:
            query = """
                SELECT ROUND((1 - SUM(getmisses) / NULLIF(SUM(gets), 0)) * 100, 2)
                FROM GV$ROWCACHE
            """
            self.c.execute(query)
            for row in self.c:
                queried_data["Dictionary Cache Hit Ratio"] = row[0] if row[0] is not None else 0
                break
        except Exception as e:
            queried_data['status'] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_global_cache_service_metrics(self):
        """
        Global Cache Service Utilization, Average Block Receive Time, Block Access Latency
        from GV$SYSMETRIC.
        """
        queried_data = {}
        gc_metrics = {
            "Global Cache Blocks Lost":              "Global Cache Blocks Lost",
            "Global Cache Blocks Corrupted":         "Global Cache Blocks Corrupted",
            "GC CR Block Received Per Second":       "GC CR Block Received Per Second",
            "GC Current Block Received Per Second":  "GC Current Block Received Per Second",
            "GC Average CR Get Time":                "GC Average CR Get Time",
            "GC Average Current Get Time":           "GC Average Current Get Time",
        }
        try:
            # Global Cache Average Block Receive Time: avg of CR + Current get times
            self.c.execute("""
                SELECT METRIC_NAME, AVG(VALUE)
                FROM GV$SYSMETRIC
                WHERE METRIC_NAME IN (
                    'GC Average CR Get Time',
                    'GC Average Current Get Time',
                    'Global Cache Blocks Lost',
                    'Global Cache Blocks Corrupted'
                )
                GROUP BY METRIC_NAME
            """)
            cr_time = 0
            curr_time = 0
            cnt = 0
            for row in self.c:
                metric_name, value = row
                value = float(value) if value else 0
                if metric_name == "GC Average CR Get Time":
                    cr_time = value
                    cnt += 1
                elif metric_name == "GC Average Current Get Time":
                    curr_time = value
                    cnt += 1

            avg_receive_time = round((cr_time + curr_time) / 2, 4) if cnt == 2 else cr_time or curr_time
            queried_data["Global Cache Average Block Receive Time"] = avg_receive_time
            queried_data["Global Cache Block Access Latency"] = avg_receive_time  # same source, represents end-to-end latency

            # Global Cache Service Utilization: total GC blocks received across instances
            self.c.execute("""
                SELECT NVL(SUM(value), 0)
                FROM GV$SYSSTAT
                WHERE LOWER(name) IN ('gc cr blocks received', 'gc current blocks received')
            """)
            for row in self.c:
                queried_data["Global Cache Service Utilization"] = row[0] if row[0] else 0
                break

        except Exception as e:
            queried_data['status'] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_tablespace_metrics(self):
        db_block_size = 8192
        try:
            self.c.execute("SELECT value FROM v$parameter WHERE name = 'db_block_size'")
            for row in self.c:
                db_block_size = row[0]
                break
        except Exception:
            pass

        queried_data = {}
        try:
            query = """
                SELECT b.TABLESPACE_NAME, d.*, b.CONTENTS, b.LOGGING, b.STATUS
                FROM dba_tablespace_usage_metrics d
                FULL JOIN dba_tablespaces b ON d.TABLESPACE_NAME = b.TABLESPACE_NAME
            """
            self.c.execute(query)
            tbs_list = []
            for row in self.c:
                tbs_dict = {}
                tbs_dict["name"] = row[0]
                tbs_dict['Used_Space'] = int(row[2]) * int(db_block_size) / 1024 / 1024 if row[2] else 0
                tbs_dict['Tablespace_Size'] = int(row[3]) * int(db_block_size) / 1024 / 1024 if row[3] else 0
                tbs_dict['Used_Percent'] = row[4] if row[4] else 0
                if row[7] == "OFFLINE":
                    tbs_dict['TB_Status'] = 0
                    tbs_dict['status'] = 0
                else:
                    tbs_dict['TB_Status'] = 1
                    tbs_dict['status'] = 1
                tbs_list.append(tbs_dict)
            queried_data['Tablespace_Details'] = tbs_list
        except Exception as e:
            queried_data["status"] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_tablespace_datafile(self):
        queried_data = {}
        try:
            query = """
                SELECT TABLESPACE_NAME, FILE_NAME,
                       (BYTES/1024/1024), BLOCKS, AUTOEXTENSIBLE,
                       (MAXBYTES/1024/1024), (MAXBLOCKS/1024/1024),
                       INCREMENT_BY, (USER_BYTES/1024/1024), USER_BLOCKS
                FROM DBA_DATA_FILES
            """
            self.c.execute(query)
            tbs_list = []
            for row in self.c:
                tb_dict = {}
                tb_dict["name"] = row[1].split("/")[-1]
                tb_dict["Data_File_Size"] = row[2]
                tb_dict["Data_File_Blocks"] = row[3]
                tb_dict["Autoextensible"] = 1 if row[4] == "YES" else 0
                tb_dict["Max_Data_File_Size"] = row[5]
                tb_dict["Max_Data_File_Blocks"] = row[6]
                tb_dict["Increment_By"] = row[7]
                tb_dict["Usable_Data_File_Size"] = row[8]
                tb_dict["Usable_Data_File_Blocks"] = row[9]
                tbs_list.append(tb_dict)
            queried_data["Tablespace_Datafile_Details"] = tbs_list
        except Exception as e:
            queried_data["status"] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def tablespace_complete(self):
        queried_data = {}
        try:
            query_output_data = self.execute_tablespace_metrics()
            queried_data.update(query_output_data)
            if 'status' in queried_data and queried_data['status'] == 0:
                return queried_data
            query_output_data = self.execute_tablespace_datafile()
            queried_data.update(query_output_data)
        except Exception as e:
            queried_data["status"] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_pdb(self):
        queried_data = {}
        try:
            query = """
                SELECT a.PDB_NAME, a.PDB_ID, a.STATUS,
                       b.OPEN_MODE, b.RESTRICTED, b.OPEN_TIME,
                       b.total_size/1024/1024, b.BLOCK_SIZE
                FROM DBA_PDBS a
                JOIN V$PDBS b ON a.PDB_NAME = b.NAME
            """
            self.c.execute(query)
            pdb_list = []
            for row in self.c:
                pdb_dict = {}
                pdb_dict['name'] = row[0]
                pdb_dict['PDB_ID'] = row[1]
                pdb_dict['PDB_Size'] = row[6]
                pdb_dict['Block_Size'] = row[7]
                pdb_list.append(pdb_dict)
            queried_data['PDB_Details'] = pdb_list
        except Exception as e:
            queried_data['status'] = 0
            queried_data['msg'] = str(e)
        return queried_data

    def execute_asm_metrics(self):
        queried_data = {}
        try:
            query = """
                SELECT name,
                       ROUND(total_mb / 1024, 2),
                       ROUND(free_mb / 1024, 2),
                       ROUND((free_mb / NULLIF(total_mb,0)) * 100, 2),
                       USABLE_FILE_MB,
                       REQUIRED_MIRROR_FREE_MB
                FROM v$asm_diskgroup
            """
            self.c.execute(query)
            asm_list = []
            for row in self.c:
                asm_list.append({
                    "name": row[0],
                    "ASM_TOTAL_GB": row[1],
                    "ASM_FREE_GB": row[2],
                    "ASM_PCT_FREE": row[3],
                    "ASM_LIMIT": row[4],
                    "ASM_THRESHOLD": row[5]
                })
            queried_data['ASM_Details'] = asm_list
        except Exception:
            queried_data['ASM_Details'] = []
        return queried_data

    def execute_db_info(self):
        query = """
            SELECT cdb AS "CDB",
                   open_mode AS "Open Mode",
                   TO_CHAR(created, 'YYYY-MM-DD HH24:MI:SS') AS "Created Date",
                   log_mode AS "Log Mode",
                   switchover_status AS "Switchover Status",
                   protection_mode AS "Protection Mode",
                   current_scn AS "Current SCN"
            FROM v$database
        """
        return self.execute_query_row_col(query)

    def metriccollector(self):
        if self.tls == "true":
            dsn = f"""(DESCRIPTION=
                    (ADDRESS=(PROTOCOL=tcps)(HOST={self.hostname})(PORT={self.port}))
                    (CONNECT_DATA=(SERVICE_NAME={self.sid}))
                    (SECURITY=(MY_WALLET_DIRECTORY={self.wallet_location}))
                    )"""
        else:
            dsn = f"{self.hostname}:{self.port}/{self.sid}"

        connection_status = self.connect(dsn)
        if not connection_status[0]:
            self.maindata['status'] = 0
            self.maindata['msg'] = connection_status[1]
            self.close_connection()
            return self.maindata

        # --- Collect all RAC metric groups ---
        collectors = [
            self.execute_sysmetric_bulk,
            self.execute_sysstat_bulk,
            self.execute_gc_wait_metrics,
            self.execute_interconnect_metrics,
            self.execute_session_metrics,
            self.execute_rac_node_metrics,
            self.execute_dictionary_cache_hit_ratio,
            self.execute_global_cache_service_metrics,
            self.tablespace_complete,
            self.execute_pdb,
            self.execute_asm_metrics,
            self.execute_db_info,
        ]

        for collector in collectors:
            try:
                result = collector()
                if result:
                    self.maindata.update(result)
                    if self.maindata.get('status') == 0:
                        self.close_connection()
                        return self.maindata
            except Exception as e:
                self.maindata['status'] = 0
                self.maindata['msg'] = str(e)
                self.close_connection()
                return self.maindata

        # --- Dashboard tab layout ---
        self.maindata['tabs'] = {
            "RAC Node Health": {
                "order": 1,
                "tablist": [
                    "Active RAC Nodes",
                    "RAC Nodes Down",
                    "RAC_Node_Details"
                ]
            },
            "Global Cache & Interconnect": {
                "order": 2,
                "tablist": [
                    "GC CR Block Received Per Second",
                    "GC Current Block Received Per Second",
                    "GC Average CR Get Time",
                    "GC Average Current Get Time",
                    "Global Cache Blocks Lost",
                    "Global Cache Blocks Corrupted",
                    "GC CR Blocks Served Per Second",
                    "GC Current Blocks Served Per Second",
                    "GC CR Block Received Total",
                    "GC Current Block Received Total",
                    "Global Cache Average Block Receive Time",
                    "Global Cache Block Access Latency",
                    "Global Cache Service Utilization",
                    "Interconnect Bytes Received Per Second",
                    "Interconnect Bytes Sent Per Second"
                ]
            },
            "GC Wait Analysis": {
                "order": 3,
                "tablist": [
                    "GC CR Request Avg Wait Time",
                    "GC Current Request Avg Wait Time",
                    "GC CR Block Busy Avg Wait Time",
                    "GC Current Block Busy Avg Wait Time",
                    "GC Buffer Busy Acquire Avg Wait Time",
                    "GC Buffer Busy Release Avg Wait Time",
                    "GC CR Request Wait Count",
                    "GC Current Request Wait Count",
                    "GC CR Block Busy Wait Count",
                    "GC Current Block Busy Wait Count",
                    "GC Buffer Busy Acquire Wait Count",
                    "GC Buffer Busy Release Wait Count"
                ]
            },
            "Session & User Activity": {
                "order": 4,
                "tablist": [
                    "Active Users",
                    "Buffer Cache Hit Ratio",
                    "Dictionary Cache Hit Ratio",
                    "Sort Ratio",
                    "Average Enqueue Timeouts",
                    "Long Queries Count",
                    "Long Queries Elapsed Time",
                    "User Locks",
                    "Locked Users"
                ]
            },
            "I/O & ASM": {
                "order": 5,
                "tablist": [
                    "Database File IO Reads",
                    "Database File IO Write Operations",
                    "Redo Log Contentions",
                    "ASM_Details"
                ]
            },
            "Tablespace and PDB": {
                "order": 6,
                "tablist": [
                    "Tablespace_Details",
                    "Tablespace_Datafile_Details",
                    "PDB_Details"
                ]
            }
        }

        self.maindata['units'] = METRICS_UNITS
        self.maindata['s247config'] = {
            "childdiscovery": [
                "Tablespace_Details",
                "Tablespace_Datafile_Details",
                "PDB_Details",
                "ASM_Details",
                "RAC_Node_Details"
            ]
        }

        self.close_connection()
        return self.maindata


def clean_quotes(value):
    if not value:
        return value
    value_str = str(value)
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        return value_str[1:-1]
    return value_str


def run(param):
    hostname = clean_quotes(param.get("hostname")) if param and param.get("hostname") else "localhost"
    port = clean_quotes(param.get("port")) if param and param.get("port") else "1521"
    sid = clean_quotes(param.get("sid")) if param and param.get("sid") else "ORCL"
    username = clean_quotes(param.get("username")) if param and param.get("username") else "None"
    password = clean_quotes(param.get("password")) if param and param.get("password") else "None"
    tls = clean_quotes(param.get("tls")) if param and param.get("tls") else "false"
    wallet_location = clean_quotes(param.get("wallet_location")) if param and param.get("wallet_location") else "None"
    oracle_home = clean_quotes(param.get("oracle_home")) if param and param.get("oracle_home") else None

    if oracle_home in ["None", "", "null"]:
        oracle_home = None

    class Args:
        def __init__(self, hostname, port, sid, username, password, tls, wallet_location, oracle_home):
            self.hostname = hostname
            self.port = port
            self.sid = sid
            self.username = username
            self.password = password
            self.tls = tls
            self.wallet_location = wallet_location
            self.oracle_home = oracle_home

    args = Args(hostname, port, sid, username, password, tls, wallet_location, oracle_home)
    oracle_instance = oracle(args)
    return oracle_instance.metriccollector()


if __name__ == "__main__":
    hostname = "localhost"
    port = "1521"
    sid = "ORCL"
    username = "ORACLE_USER"
    password = "ORACLE_USER"
    tls = "False"
    wallet_location = None
    oracle_home = None

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--hostname', default=hostname)
    parser.add_argument('--port', default=port)
    parser.add_argument('--sid', default=sid)
    parser.add_argument('--username', default=username)
    parser.add_argument('--password', default=password)
    parser.add_argument('--tls', default=tls)
    parser.add_argument('--wallet_location', default=wallet_location)
    parser.add_argument('--oracle_home', default=oracle_home)

    args = parser.parse_args()

    if args.oracle_home and os.path.exists(args.oracle_home):
        os.environ['ORACLE_HOME'] = args.oracle_home

    obj = oracle(args)
    result = obj.metriccollector()
    print(json.dumps(result, default=str))
