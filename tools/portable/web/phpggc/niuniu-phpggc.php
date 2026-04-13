#!/usr/bin/env php
<?php

declare(strict_types=1);

chdir(__DIR__);

$bootstrapRoot = __DIR__ . '/lib/PHPGGC';
$iterator = new RecursiveIteratorIterator(
    new RecursiveDirectoryIterator($bootstrapRoot, FilesystemIterator::SKIP_DOTS),
    RecursiveIteratorIterator::LEAVES_ONLY
);

foreach ($iterator as $fileInfo) {
    if ($fileInfo->getExtension() !== 'php') {
        continue;
    }
    require_once $fileInfo->getPathname();
}

require_once __DIR__ . '/lib/PHPGGC.php';

$runner = new PHPGGC();

try {
    $runner->generate();
} catch (\PHPGGC\Exception $exception) {
    fwrite(STDERR, "ERROR: " . $exception->getMessage() . PHP_EOL);
    exit(1);
}
