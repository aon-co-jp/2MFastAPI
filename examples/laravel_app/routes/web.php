<?php
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\UserController;
use App\Http\Controllers\PhotoController;

Route::get('/', function () {
    return 'Hello from Laravel';
})->name('home');

Route::get('/hello/{name}', function ($name) {
    return 'Hello, ' . $name . '!';
});

Route::get('/dashboard', function () {
    $users = User::all();
    $title = '<b>Team</b>';
    return view('dashboard', compact('users', 'title'));
});

Route::get('/page/{name}', fn ($name) => view('hello', ['name' => $name]));

Route::get('/greet/{name}', function ($name) {
    return "Hi {$name}, welcome!";
});

Route::get('/users', [UserController::class, 'index']);
Route::get('/users/{id}', 'UserController@show');

Route::prefix('admin')->name('admin.')->group(function () {
    Route::get('/stats', function () {
        return ['ok' => 1];
    })->name('stats');
    Route::prefix('v')->group(function () {
        Route::get('/ping', function () {
            return 'pong';
        });
    });
});

Route::middleware('auth')->group(function () {
    Route::get('/secret', function () {
        return 'secret';
    });
});

Route::controller(UserController::class)->prefix('ctl')->group(function () {
    Route::get('/list', 'index');
    Route::get('/show/{id}', 'show');
});

Route::resource('photos', PhotoController::class);

Route::get('/search', function (Request $request) {
    return ['q' => $request->query('q', '')];
});
