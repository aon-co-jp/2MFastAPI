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

Route::get('/greet/{name}', function ($name) {
    return "Hi {$name}, welcome!";
});

Route::get('/users', [UserController::class, 'index']);
Route::get('/users/{id}', 'UserController@show');

Route::prefix('admin')->group(function () {
    Route::get('/stats', function () {
        return ['ok' => 1];
    });
    Route::prefix('v')->group(function () {
        Route::get('/ping', function () {
            return 'pong';
        });
    });
});
