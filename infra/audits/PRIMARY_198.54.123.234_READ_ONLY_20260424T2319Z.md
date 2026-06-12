# Primary legacy server — read-only audit

**Host:** `nc-ph-0934-24` · **When (UTC):** 2026-04-24 23:20 UTC

## 1. Identity & resources
```
Kernel: 5.15.0-164-generic
Uptime: up 11 weeks, 4 days, 22 hours, 27 minutes
model name	: Intel(R) Xeon(R) CPU E3-1270 v3 @ 3.50GHz
processor	: 0
MemTotal:        8085784 kB
```

## 2. Disk (top pressure)
```
Filesystem     Type   Size  Used Avail Use% Mounted on
tmpfs          tmpfs  790M  992K  789M   1% /run
/dev/sda3      ext4   438G   78G  338G  19% /
tmpfs          tmpfs  3.9G   28K  3.9G   1% /dev/shm
tmpfs          tmpfs  5.0M     0  5.0M   0% /run/lock
/dev/sda2      ext4   2.0G  252M  1.6G  14% /boot
tmpfs          tmpfs  790M  4.0K  790M   1% /run/user/0
```

### Largest under /opt/fpai (depth aggregate, top 15)
```
14290932	/opt/fpai
4940720	/opt/fpai/SERVICES
3619036	/opt/fpai/backups
3193840	/opt/fpai/services
1819380	/opt/fpai/backups/services
1683592	/opt/fpai/SERVICES/fiart
1330920	/opt/fpai/core
1328060	/opt/fpai/core/applications
1290392	/opt/fpai/backups/websites
1139216	/opt/fpai/SERVICES/concierge
746504	/opt/fpai/services/ai-brain
711600	/opt/fpai/services/music-maestro
491844	/opt/fpai/backups/dashboards
313704	/opt/fpai/SERVICES/consciousness_optimizer
277388	/opt/fpai/services/legal-guardian
```

## 3. Listening TCP
```
State  Recv-Q Send-Q  Local Address:Port Peer Address:PortProcess                                                                                                                                                                                                                                                             
LISTEN 0      128           0.0.0.0:8022      0.0.0.0:*    users:(("sshd",pid=650,fd=3))                                                                                                                                                                                                                                      
LISTEN 0      2048          0.0.0.0:8120      0.0.0.0:*    users:(("python",pid=116751,fd=7))                                                                                                                                                                                                                                 
LISTEN 0      244         127.0.0.1:5432      0.0.0.0:*    users:(("postgres",pid=3990036,fd=6))                                                                                                                                                                                                                              
LISTEN 0      4096    127.0.0.53%lo:53        0.0.0.0:*    users:(("systemd-resolve",pid=628,fd=14))                                                                                                                                                                                                                          
LISTEN 0      2048        127.0.0.1:8823      0.0.0.0:*    users:(("uvicorn",pid=3990230,fd=13))                                                                                                                                                                                                                              
LISTEN 0      2048        127.0.0.1:8822      0.0.0.0:*    users:(("uvicorn",pid=3990220,fd=13))                                                                                                                                                                                                                              
LISTEN 0      2048        127.0.0.1:8821      0.0.0.0:*    users:(("uvicorn",pid=3990225,fd=13))                                                                                                                                                                                                                              
LISTEN 0      2048        127.0.0.1:8820      0.0.0.0:*    users:(("uvicorn",pid=3990215,fd=13))                                                                                                                                                                                                                              
LISTEN 0      2048        127.0.0.1:8825      0.0.0.0:*    users:(("uvicorn",pid=3990235,fd=13))                                                                                                                                                                                                                              
LISTEN 0      2048        127.0.0.1:8824      0.0.0.0:*    users:(("uvicorn",pid=3981574,fd=13))                                                                                                                                                                                                                              
LISTEN 0      244    198.54.123.234:5432      0.0.0.0:*    users:(("postgres",pid=3990036,fd=7))                                                                                                                                                                                                                              
LISTEN 0      5           127.0.0.1:8199      0.0.0.0:*    users:(("python3",pid=1745804,fd=3))                                                                                                                                                                                                                               
LISTEN 0      128           0.0.0.0:2222      0.0.0.0:*    users:(("sshd",pid=650,fd=5))                                                                                                                                                                                                                                      
LISTEN 0      5           127.0.0.1:8191      0.0.0.0:*    users:(("python3",pid=3468894,fd=3))                                                                                                                                                                                                                               
LISTEN 0      100           0.0.0.0:995       0.0.0.0:*    users:(("dovecot",pid=3047626,fd=22))                                                                                                                                                                                                                              
LISTEN 0      100           0.0.0.0:993       0.0.0.0:*    users:(("dovecot",pid=3047626,fd=37))                                                                                                                                                                                                                              
LISTEN 0      2048          0.0.0.0:8770      0.0.0.0:*    users:(("python3",pid=3707073,fd=13))                                                                                                                                                                                                                              
LISTEN 0      100           0.0.0.0:587       0.0.0.0:*    users:(("smtpd",pid=3995491,fd=6),("smtpd",pid=3994580,fd=6),("master",pid=2995918,fd=18))                                                                                                                                                                         
LISTEN 0      2048          0.0.0.0:8800      0.0.0.0:*    users:(("uvicorn",pid=1740113,fd=15))                                                                                                                                                                                                                              
LISTEN 0      128           0.0.0.0:8750      0.0.0.0:*    users:(("python3",pid=1745137,fd=3))                                                                                                                                                                                                                               
LISTEN 0      2048          0.0.0.0:8765      0.0.0.0:*    users:(("python3",pid=440356,fd=16))                                                                                                                                                                                                                               
LISTEN 0      2048          0.0.0.0:8850      0.0.0.0:*    users:(("uvicorn",pid=1740166,fd=15))                                                                                                                                                                                                                              
LISTEN 0      2048          0.0.0.0:8550      0.0.0.0:*    users:(("python",pid=3992865,fd=7))                                                                                                                                                                                                                                
LISTEN 0      2048          0.0.0.0:8651      0.0.0.0:*    users:(("python",pid=1746352,fd=6))                                                                                                                                                                                                                                
LISTEN 0      2048          0.0.0.0:8660      0.0.0.0:*    users:(("python",pid=1745589,fd=6))                                                                                                                                                                                                                                
LISTEN 0      511           0.0.0.0:8602      0.0.0.0:*    users:(("nginx",pid=3992340,fd=13),("nginx",pid=3992339,fd=13),("nginx",pid=3992338,fd=13),("nginx",pid=3992337,fd=13),("nginx",pid=3992336,fd=13),("nginx",pid=3992335,fd=13),("nginx",pid=3992334,fd=13),("nginx",pid=3992333,fd=13),("nginx",pid=1746671,fd=13))
LISTEN 0      2048          0.0.0.0:8601      0.0.0.0:*    users:(("python3",pid=2721291,fd=17))                                                                                                                                                                                                                              
LISTEN 4      2048          0.0.0.0:8600      0.0.0.0:*    users:(("python3",pid=3995267,fd=20))                                                                                                                                                                                                                              
LISTEN 0      511           0.0.0.0:443       0.0.0.0:*    users:(("nginx",pid=3992340,fd=7),("nginx",pid=3992339,fd=7),("nginx",pid=3992338,fd=7),("nginx",pid=3992337,fd=7),("nginx",pid=3992336,fd=7),("nginx",pid=3992335,fd=7),("nginx",pid=3992334,fd=7),("nginx",pid=3992333,fd=7),("nginx",pid=1746671,fd=7))         
LISTEN 0      511           0.0.0.0:80        0.0.0.0:*    users:(("nginx",pid=3992340,fd=6),("nginx",pid=3992339,fd=6),("nginx",pid=3992338,fd=6),("nginx",pid=3992337,fd=6),("nginx",pid=3992336,fd=6),("nginx",pid=3992335,fd=6),("nginx",pid=3992334,fd=6),("nginx",pid=3992333,fd=6),("nginx",pid=1746671,fd=6))         
LISTEN 0      100           0.0.0.0:110       0.0.0.0:*    users:(("dovecot",pid=3047626,fd=21))                                                                                                                                                                                                                              
LISTEN 0      128           0.0.0.0:22        0.0.0.0:*    users:(("sshd",pid=650,fd=7))                                                                                                                                                                                                                                      
LISTEN 0      100           0.0.0.0:25        0.0.0.0:*    users:(("smtpd",pid=3995295,fd=6),("master",pid=2995918,fd=13))                                                                                                                                                                                                    
LISTEN 0      511         127.0.0.1:6379      0.0.0.0:*    users:(("redis-server",pid=3991430,fd=6))                                                                                                                                                                                                                          
LISTEN 0      100           0.0.0.0:143       0.0.0.0:*    users:(("dovecot",pid=3047626,fd=36))                                                                                                                                                                                                                              
LISTEN 0      128              [::]:8022         [::]:*    users:(("sshd",pid=650,fd=4))                                                                                                                                                                                                                                      
LISTEN 0      128              [::]:2222         [::]:*    users:(("sshd",pid=650,fd=6))                                                                                                                                                                                                                                      
LISTEN 0      100              [::]:587          [::]:*    users:(("smtpd",pid=3995491,fd=7),("smtpd",pid=3994580,fd=7),("master",pid=2995918,fd=19))                                                                                                                                                                         
LISTEN 0      244             [::1]:5432         [::]:*    users:(("postgres",pid=3990036,fd=5))                                                                                                                                                                                                                              
LISTEN 0      511              [::]:443          [::]:*    users:(("nginx",pid=3992340,fd=8),("nginx",pid=3992339,fd=8),("nginx",pid=3992338,fd=8),("nginx",pid=3992337,fd=8),("nginx",pid=3992336,fd=8),("nginx",pid=3992335,fd=8),("nginx",pid=3992334,fd=8),("nginx",pid=3992333,fd=8),("nginx",pid=1746671,fd=8))         
LISTEN 0      511              [::]:80           [::]:*    users:(("nginx",pid=3992340,fd=9),("nginx",pid=3992339,fd=9),("nginx",pid=3992338,fd=9),("nginx",pid=3992337,fd=9),("nginx",pid=3992336,fd=9),("nginx",pid=3992335,fd=9),("nginx",pid=3992334,fd=9),("nginx",pid=3992333,fd=9),("nginx",pid=1746671,fd=9))         
LISTEN 0      128              [::]:22           [::]:*    users:(("sshd",pid=650,fd=8))                                                                                                                                                                                                                                      
LISTEN 0      100              [::]:25           [::]:*    users:(("smtpd",pid=3995295,fd=7),("master",pid=2995918,fd=14))                                                                                                                                                                                                    
```

## 4. systemd — failed
```
failed-unit-count: 0
```

## 5. Running services (filtered)
```
  fpai-ad-portal.service             loaded active running FPAI Ad Portal - Facebook/Meta Advertising Management
  fpai-cocoon.service                loaded active running COCOON Command Center
  fpai-credits-gateway.service       loaded active running FP Credits Gateway - Unified Credits API
  fpai-fp-index.service              loaded active running Full Potential Index v5.5.0 — Constitutional Intelligence Economy
  fpai-lead-capture.service          loaded active running FPAI Lead Capture API
  fpai-nerve-center.service          loaded active running FPAI Nerve Center - System Integration Hub
  fpai-projects.service              loaded active running Full Potential Projects Dashboard
  nginx.service                      loaded active running A high performance web server and a reverse proxy server
  postgresql@14-main.service         loaded active running PostgreSQL Cluster 14-main
  redis-server.service               loaded active running Advanced key-value store
```

## 6. Docker
```
```

## 7. Cron
```
### root crontab
# ============================================
# FPAI PRIMARY SERVER — CLEANED March 16, 2026
# ============================================
# Removed 18 malware cron entries (/tmp/x86_64.kok)
# Backup: /opt/fpai/backups/primary-crontab-backup-*.txt

# SSH watchdog
*/5 * * * * systemctl is-active sshd || systemctl restart sshd

# Credits DB backup (every 6 hours)
0 */6 * * * /opt/fpai/scripts/backup-credits-db.sh >> /var/log/credits-backup.log 2>&1

# Weekly memory hygiene
0 3 * * 0 /opt/fpai/scripts/memory-hygiene.sh

# Email relay monitor
*/5 * * * * /opt/fpai/email-relay/monitor.sh

### /etc/cron.d (filenames)
total 40
drwxr-xr-x   2 root root  4096 Mar 16 18:17 .
drwxr-xr-x 137 root root 12288 Mar 16 18:18 ..
-rw-r--r--   1 root root   775 Sep 14  2018 certbot
-rw-r--r--   1 root root   201 Jan  8  2022 e2scrub_all
-rw-r--r--   1 root root   249 Dec 10 09:52 fee_settlement
-rw-r--r--   1 root root    86 Nov 29 05:15 fiart-health-check
-rw-r--r--   1 root root   102 Mar 23  2022 .placeholder
-rw-r--r--   1 root root   396 Feb  2  2021 sysstat
```

## 8. Journal errors (tail, last 7d)
```
Apr 24 21:01:37 nc-ph-0934-24 sshd[3975388]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:05:01 nc-ph-0934-24 sshd[3975633]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:10:01 nc-ph-0934-24 sshd[3975952]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:11:02 nc-ph-0934-24 sshd[3976014]: error: kex_exchange_identification: banner line contains invalid characters
Apr 24 21:15:01 nc-ph-0934-24 sshd[3976285]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:20:01 nc-ph-0934-24 sshd[3976605]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:25:01 nc-ph-0934-24 sshd[3976933]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:30:01 nc-ph-0934-24 sshd[3977263]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:35:01 nc-ph-0934-24 sshd[3977591]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:40:01 nc-ph-0934-24 sshd[3977858]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:45:01 nc-ph-0934-24 sshd[3978140]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:50:01 nc-ph-0934-24 sshd[3978460]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 21:55:01 nc-ph-0934-24 sshd[3978766]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:00:01 nc-ph-0934-24 sshd[3979076]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:05:01 nc-ph-0934-24 sshd[3979386]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:10:01 nc-ph-0934-24 sshd[3979717]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:15:01 nc-ph-0934-24 sshd[3980020]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:20:01 nc-ph-0934-24 sshd[3981062]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:23:51 nc-ph-0934-24 sshd[3982326]: error: kex_exchange_identification: read: Connection reset by peer
Apr 24 22:25:01 nc-ph-0934-24 sshd[3983163]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:30:01 nc-ph-0934-24 sshd[3983886]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:35:01 nc-ph-0934-24 sshd[3985357]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:40:01 nc-ph-0934-24 sshd[3986803]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:45:01 nc-ph-0934-24 sshd[3987703]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:46:55 nc-ph-0934-24 sshd[3988029]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:47:26 nc-ph-0934-24 sshd[3988095]: error: maximum authentication attempts exceeded for root from 103.176.90.41 port 17742 ssh2 [preauth]
Apr 24 22:48:45 nc-ph-0934-24 sshd[3988359]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:50:01 nc-ph-0934-24 sshd[3988941]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 22:55:01 nc-ph-0934-24 sshd[3989911]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 23:00:01 nc-ph-0934-24 sshd[3991281]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 23:05:01 nc-ph-0934-24 sshd[3992540]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 23:07:56 nc-ph-0934-24 sshd[3993044]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 23:10:01 nc-ph-0934-24 sshd[3993277]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 23:15:01 nc-ph-0934-24 sshd[3994067]: error: kex_exchange_identification: Connection closed by remote host
Apr 24 23:20:02 nc-ph-0934-24 sshd[3995758]: error: kex_exchange_identification: Connection closed by remote host
```

## 9. Security spot checks (read-only)
```
### .env under /opt/fpai, perm != 600
/opt/fpai/.env
/opt/fpai/archive/legacy/whaletrack-minnow-20251205/.env
/opt/fpai/archive/whaletrack-magnet-LEGACY/.env
/opt/fpai/services/ai-brain/.env
/opt/fpai/services/fp-chat-agent/.env
/opt/fpai/services/ad-portal/.env
/opt/fpai/services/fp-index/.env
/opt/fpai/services/fp-credits-gateway/.env
/opt/fpai/services/outbounders-integration/.env
/opt/fpai/services/whiterock-blessings/.env
/opt/fpai/services/team-hub/.env
/opt/fpai/services/whaletrack-magnet/.env
/opt/fpai/SERVICES/fiart/.env
/opt/fpai/SERVICES/zen-village/.env
/opt/fpai/SERVICES/content-studio/.env
/opt/fpai/backups/whaletrack-magnet-v2.5.0-20251201/.env
/opt/fpai/backups/services/fiart/v2.0.0-pre-sacredgate_20251129_013854/.env
/opt/fpai/backups/services/sparket-engine/v1.0.3_20251213_064729/.env
/opt/fpai/backups/services/sparket-engine/v1.0.1_20251212_165747/.env
/opt/fpai/backups/services/sparket-engine/v1.0.0_20251212_164919/.env
/opt/fpai/backups/services/sparket-engine/v1.0.2_20251212_170129/.env
/opt/fpai/backups/services/sparket-engine/v1.0.2_20251212_180105/.env
/opt/fpai/backups/services/sparket-engine/v1.0.4_20251213_065037/.env
/opt/fpai/backups/services/content-studio/v0.initial_20251127_174636/.env
/opt/fpai/backups/whaletrack-magnet-v2.1-pre-multisignal-20251127_135437/.env
/opt/fpai/voice-server/.env
/opt/fpai/aria/.env
/opt/fpai/voice-phone/.env
/opt/fpai/sparket-engine/.env
/opt/fpai/discord-bot/.env

### world-writable files under /opt/fpai (sample)
/opt/fpai/archive/whaletrack-magnet-LEGACY/data/subscriptions.db
/opt/fpai/core/applications/website-ai/frontend/projects/inboundleads/state.json
```

## 10. OOM / pressure (journal grep, 14d)
```
```

## Adam — prioritize
1. Fix **failed systemd** units (reliability).
2. Reconcile **unexpected LISTEN** ports with SERVICE_REGISTRY intent.
3. **Disk hogs** under /opt/fpai — log rotation / archives before incidents.
4. **chmod 600** any secret .env files flagged above.
5. **Cron** inventory: remove dead pollers / duplicate jobs (cost + noise).

---
*Read-only audit; no changes were made on this host.*
