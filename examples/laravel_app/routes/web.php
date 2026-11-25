<?php
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return 'Hello from Laravel';
});

Route::get('/hello/{name}', function ($name) {
    return 'Hello, ' . $name . '!';
});

Route::get('/dashboard', function () {
    return view('dashboard');
});
