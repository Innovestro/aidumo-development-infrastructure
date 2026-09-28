<?php
// Synthetic substrate probe only; never an Aidumo application qualification.
declare(strict_types=1);
header('Content-Type: application/json');
$required = explode(' ', 'ctype curl dom fileinfo filter hash intl json libxml mbstring openssl pcre PDO pdo_mysql session sodium tokenizer xml xmlreader xmlwriter zip Phar');
$limits = [];
foreach (explode(' ', 'memory_limit max_execution_time max_input_time upload_max_filesize post_max_size max_input_vars default_socket_timeout') as $name) {
    $limits[$name] = ini_get($name);
}
$pdo = new PDO('mysql:unix_socket=/var/run/mysql/mysql.sock;charset=utf8mb4', 'b6web', null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$dbMarker = $pdo->query('SELECT value FROM b6_persistence.marker WHERE id = 1')->fetchColumn();
echo json_encode([
    'db_user' => $pdo->query('SELECT CURRENT_USER()')->fetchColumn(),
    'db_marker' => $dbMarker,
    'php' => PHP_VERSION, 'sapi' => PHP_SAPI,
    'missing' => array_values(array_filter($required, fn($m) => !extension_loaded($m))),
    'limits' => $limits, 'document_root' => $_SERVER['DOCUMENT_ROOT'] ?? null,
    'script' => __FILE__, 'uri' => $_SERVER['REQUEST_URI'] ?? null,
    'https' => $_SERVER['HTTPS'] ?? null,
    'private_writable' => is_writable('/var/db/aidumo-b6/private'),
    'public_writable' => is_writable(__DIR__),
    'http_proxy' => $_SERVER['HTTP_PROXY'] ?? null,
], JSON_THROW_ON_ERROR | JSON_PRETTY_PRINT), "\n";
