CREATE TABLE IF NOT EXISTS sites (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    site_name VARCHAR(255) NOT NULL,
    site_slug VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_sites_site_name (site_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS hosts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    site_id BIGINT UNSIGNED NOT NULL,
    host_address VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    prompt_host VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_hosts_site_host (site_id, host_address),
    CONSTRAINT fk_hosts_site
        FOREIGN KEY (site_id) REFERENCES sites(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS services (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    host_id BIGINT UNSIGNED NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    service_slug VARCHAR(255) NOT NULL,
    check_profile_name VARCHAR(255) NOT NULL,
    protocol VARCHAR(32) NOT NULL DEFAULT 'ssh',
    ssh_port INT NOT NULL DEFAULT 22,
    username VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_services_host_service (host_id, service_name),
    CONSTRAINT fk_services_host
        FOREIGN KEY (host_id) REFERENCES hosts(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS web_targets (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    site_id BIGINT UNSIGNED NOT NULL,
    target_name VARCHAR(255) NOT NULL,
    target_slug VARCHAR(255) NOT NULL,
    target_url VARCHAR(2048) NOT NULL,
    login_required TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_web_targets_site_name (site_id, target_name),
    CONSTRAINT fk_web_targets_site
        FOREIGN KEY (site_id) REFERENCES sites(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS check_runs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    run_key VARCHAR(64) NOT NULL,
    generated_at DATETIME NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'python-runner',
    overall_status VARCHAR(32) NOT NULL,
    total_hosts INT NOT NULL DEFAULT 0,
    total_services INT NOT NULL DEFAULT 0,
    total_passed INT NOT NULL DEFAULT 0,
    total_failed INT NOT NULL DEFAULT 0,
    total_web_checks INT NOT NULL DEFAULT 0,
    total_web_passed INT NOT NULL DEFAULT 0,
    total_web_failed INT NOT NULL DEFAULT 0,
    web_summary_report_path VARCHAR(1024) NOT NULL,
    raw_payload JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_check_runs_run_key (run_key),
    KEY idx_check_runs_generated_at (generated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS site_run_reports (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    check_run_id BIGINT UNSIGNED NOT NULL,
    site_id BIGINT UNSIGNED NOT NULL,
    report_html_path VARCHAR(1024) NOT NULL,
    summary_screenshot_file VARCHAR(1024) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_site_run_reports_run_site (check_run_id, site_id),
    CONSTRAINT fk_site_run_reports_run
        FOREIGN KEY (check_run_id) REFERENCES check_runs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_site_run_reports_site
        FOREIGN KEY (site_id) REFERENCES sites(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS service_results (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    check_run_id BIGINT UNSIGNED NOT NULL,
    site_id BIGINT UNSIGNED NOT NULL,
    host_id BIGINT UNSIGNED NOT NULL,
    service_id BIGINT UNSIGNED NOT NULL,
    host_address VARCHAR(255) NOT NULL,
    host_display_name VARCHAR(255) NOT NULL,
    service_name VARCHAR(255) NOT NULL,
    profile_name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    passed_count INT NOT NULL,
    failed_count INT NOT NULL,
    protocol VARCHAR(32) NOT NULL,
    ssh_port INT NOT NULL,
    raw_log LONGTEXT NOT NULL,
    connection_error TEXT NOT NULL,
    log_file VARCHAR(1024) NOT NULL,
    service_report_html_path VARCHAR(1024) NOT NULL,
    service_screenshot_file VARCHAR(1024) NOT NULL,
    generated_at DATETIME NOT NULL,
    raw_payload JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_service_results_run_service (check_run_id, service_id),
    KEY idx_service_results_run_id (check_run_id),
    KEY idx_service_results_service_generated_at (service_id, generated_at),
    KEY idx_service_results_status (status),
    CONSTRAINT fk_service_results_run
        FOREIGN KEY (check_run_id) REFERENCES check_runs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_service_results_site
        FOREIGN KEY (site_id) REFERENCES sites(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_service_results_host
        FOREIGN KEY (host_id) REFERENCES hosts(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_service_results_service
        FOREIGN KEY (service_id) REFERENCES services(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS service_check_steps (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    service_result_id BIGINT UNSIGNED NOT NULL,
    step_order INT NOT NULL,
    step_name VARCHAR(255) NOT NULL,
    command TEXT NOT NULL,
    display_command TEXT NOT NULL,
    prompt_dir VARCHAR(255) NOT NULL,
    ok TINYINT(1) NOT NULL DEFAULT 0,
    exit_code INT NOT NULL DEFAULT 0,
    duration_sec DECIMAL(12, 3) NOT NULL DEFAULT 0,
    stdout LONGTEXT NOT NULL,
    stderr LONGTEXT NOT NULL,
    runner_error TEXT NOT NULL,
    notes JSON NOT NULL,
    raw_payload JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_service_check_steps_result_order (service_result_id, step_order),
    CONSTRAINT fk_service_check_steps_result
        FOREIGN KEY (service_result_id) REFERENCES service_results(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS web_check_results (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    check_run_id BIGINT UNSIGNED NOT NULL,
    site_id BIGINT UNSIGNED NOT NULL,
    web_target_id BIGINT UNSIGNED NULL,
    target_name VARCHAR(255) NOT NULL,
    target_url VARCHAR(2048) NOT NULL,
    final_url VARCHAR(2048) NOT NULL,
    status VARCHAR(32) NOT NULL,
    login_required TINYINT(1) NOT NULL DEFAULT 0,
    message TEXT NOT NULL,
    captured_at DATETIME NOT NULL,
    screenshot_file VARCHAR(1024) NOT NULL,
    web_report_html_path VARCHAR(1024) NOT NULL,
    raw_payload JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_web_check_results_run_site_name (check_run_id, site_id, target_name),
    KEY idx_web_check_results_run_id (check_run_id),
    KEY idx_web_check_results_status (status),
    CONSTRAINT fk_web_check_results_run
        FOREIGN KEY (check_run_id) REFERENCES check_runs(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_web_check_results_site
        FOREIGN KEY (site_id) REFERENCES sites(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_web_check_results_target
        FOREIGN KEY (web_target_id) REFERENCES web_targets(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DROP VIEW IF EXISTS latest_service_status_v;
CREATE VIEW latest_service_status_v AS
SELECT
    sr.id AS service_result_id,
    sr.check_run_id,
    cr.run_key,
    cr.generated_at,
    si.site_name,
    h.host_address,
    h.display_name AS host_display_name,
    s.service_name,
    s.check_profile_name,
    sr.status,
    sr.passed_count,
    sr.failed_count,
    sr.connection_error,
    sr.service_report_html_path,
    sr.service_screenshot_file
FROM service_results sr
JOIN check_runs cr ON cr.id = sr.check_run_id
JOIN services s ON s.id = sr.service_id
JOIN hosts h ON h.id = sr.host_id
JOIN sites si ON si.id = sr.site_id
WHERE sr.id = (
    SELECT sr2.id
    FROM service_results sr2
    WHERE sr2.service_id = sr.service_id
    ORDER BY sr2.generated_at DESC, sr2.id DESC
    LIMIT 1
);

DROP VIEW IF EXISTS latest_web_status_v;
CREATE VIEW latest_web_status_v AS
SELECT
    wr.id AS web_result_id,
    wr.check_run_id,
    cr.run_key,
    cr.generated_at,
    si.site_name,
    wr.target_name,
    wr.target_url,
    wr.final_url,
    wr.status,
    wr.message,
    wr.screenshot_file,
    wr.web_report_html_path
FROM web_check_results wr
JOIN check_runs cr ON cr.id = wr.check_run_id
JOIN sites si ON si.id = wr.site_id
WHERE wr.id = (
    SELECT wr2.id
    FROM web_check_results wr2
    WHERE wr2.site_id = wr.site_id
      AND wr2.target_name = wr.target_name
    ORDER BY wr2.captured_at DESC, wr2.id DESC
    LIMIT 1
);
