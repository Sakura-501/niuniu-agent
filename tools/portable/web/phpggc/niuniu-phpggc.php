#!/usr/bin/env php
<?php

declare(strict_types=1);

chdir(__DIR__);

spl_autoload_register(static function (string $class): void {
    if (!str_starts_with($class, 'PHPGGC\\')) {
        return;
    }
    $path = __DIR__ . '/lib/' . str_replace('\\', '/', $class) . '.php';
    if (is_file($path)) {
        require_once $path;
    }
});

require_once __DIR__ . '/lib/PHPGGC.php';

$runner = new PHPGGC();

try {
    $runner->generate();
} catch (\PHPGGC\Exception $exception) {
    fwrite(STDERR, "ERROR: " . $exception->getMessage() . PHP_EOL);
    exit(1);
}
