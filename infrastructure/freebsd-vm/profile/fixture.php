<?php
// Run as b6web, via CLI. Only touches this profile's named fixture paths/schema.
declare(strict_types=1);
function check(bool $ok, string $label): void {
    if (!$ok) { throw new RuntimeException($label); }
    echo "$label=PASS\n";
}
$dir = '/var/db/aidumo-b6/private';
umask(0077);
check(is_writable($dir) && !is_writable('/usr/local/www/aidumo-b6/public'), 'private_vs_public');
check(file_put_contents("$dir/Case", 'upper') === 5, 'write_upper');
check(file_put_contents("$dir/case", 'lower') === 5, 'write_lower');
check(file_get_contents("$dir/Case") === 'upper' && file_get_contents("$dir/case") === 'lower', 'case_distinct');
check(rename("$dir/Case", "$dir/replaced"), 'same_directory_rename');
check(file_put_contents("$dir/next", 'new') === 3 && rename("$dir/next", "$dir/replaced") && file_get_contents("$dir/replaced") === 'new', 'rename_replace');
check((fileperms("$dir/replaced") & 0777) === 0600, 'private_file_mode');
$a = fopen("$dir/lock", 'c+');
$b = fopen("$dir/lock", 'c+');
check(flock($a, LOCK_EX | LOCK_NB), 'lock_first');
check(!flock($b, LOCK_EX | LOCK_NB), 'lock_contention');
$child = proc_open([PHP_BINARY, '-r', '$h=fopen($argv[1],"c+"); exit(flock($h,LOCK_EX|LOCK_NB) ? 1 : 0);', "$dir/lock"], [], $pipes);
check(is_resource($child) && proc_close($child) === 0, 'cross_process_lock_contention');
check(flock($a, LOCK_UN) && flock($b, LOCK_EX | LOCK_NB), 'lock_release');
fclose($a); fclose($b);
foreach (['replaced', 'case', 'lock'] as $file) { check(unlink("$dir/$file"), "cleanup_$file"); }
$pdo = new PDO('mysql:unix_socket=/var/run/mysql/mysql.sock;charset=utf8mb4', 'b6web', null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
check($pdo->query('SELECT value FROM b6_persistence.marker WHERE id = 1')->fetchColumn() === 'b6-persistent-v1', 'db_persistence');
check(str_starts_with($pdo->query('SELECT VERSION()')->fetchColumn(), '11.4.'), 'mariadb_version');
check($pdo->query('SELECT CURRENT_USER()')->fetchColumn() === 'b6web@localhost', 'ordinary_db_user');
$pdo->exec('CREATE DATABASE b6_fixture');
try {
    $pdo->exec('CREATE TABLE b6_fixture.probe (id INT PRIMARY KEY, value VARCHAR(32))');
    $pdo->exec("INSERT INTO b6_fixture.probe VALUES (1, 'first')");
    $pdo->exec("UPDATE b6_fixture.probe SET value = 'second' WHERE id = 1");
    check($pdo->query('SELECT value FROM b6_fixture.probe WHERE id = 1')->fetchColumn() === 'second', 'pdo_create_write_read');
    $pdo->exec('DROP TABLE b6_fixture.probe');
} finally { $pdo->exec('DROP DATABASE b6_fixture'); }
check((int)$pdo->query("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='b6_fixture'")->fetchColumn() === 0, 'pdo_drop');
try { $pdo->query('SELECT User FROM mysql.user'); throw new RuntimeException('unexpected global access'); }
catch (PDOException $e) { check($e->getCode() === '42000', 'db_global_access_denied'); }
// Retained across service/guest restart; subsequent runs verify rather than overwrite.
$marker = "$dir/persistence";
if (($argv[1] ?? null) === '--initialize-marker') {
    check(!file_exists($marker), 'marker_initially_absent');
    check(file_put_contents($marker, 'b6-persistent-v1') === 16, 'create_persistence');
}
check(is_file($marker) && file_get_contents($marker) === 'b6-persistent-v1', 'filesystem_persistence');
