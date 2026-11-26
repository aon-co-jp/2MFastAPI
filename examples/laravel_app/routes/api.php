<?php
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\UserController;

Route::get('/users/{id}', function ($id) {
    return ['id' => $id, 'role' => 'member'];
});

Route::post('/orders', function (Request $request) {
    $o = Order::create($request->all());
    return $o;
});

Route::get('/orders/status/{status}', function ($status) {
    return Order::where('status', $status)->get();
});

Route::get('/orders/big', function () {
    return Order::where('amount', '>=', 100)->where('status', 'paid')->first();
});

Route::get('/orders/{id}', function ($id) {
    return Order::findOrFail($id);
});

Route::post('/users', [UserController::class, 'store']);

Route::post('/legacy', function (Request $request) {
    $request->validate(['name' => 'required']);
    return 'x';
});
