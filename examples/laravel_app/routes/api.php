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

Route::get('/users/{user}/orders', function (User $user) {
    return $user->orders;
});

Route::get('/orders/{order}/owner', function (Order $order) {
    return $order->user;
});

Route::post('/orders/{order}/pay', function (Order $order) {
    $order->status = 'paid';
    $order->save();
    return $order;
});

Route::delete('/orders/{order}', function (Order $order) {
    $order->delete();
    return response()->json(null, 204);
});

Route::get('/report', function () {
    return [
        'count' => DB::table('orders')->where('status', 'paid')->count(),
        'top' => DB::table('orders')->orderBy('amount', 'desc')->limit(2)->pluck('amount'),
        'raw' => DB::select('select status, count(*) as n from orders where amount >= ? group by status order by status', [10]),
    ];
});

Route::post('/orders/close', function () {
    $n = DB::table('orders')->where('status', 'new')->update(['status' => 'closed']);
    DB::table('orders')->insert(['user_id' => 1, 'amount' => 5, 'status' => 'tiny']);
    return ['closed' => $n];
});

Route::get('/users/{user}/page', function (User $user) {
    $orders = $user->orders;
    return view('orders', compact('user', 'orders'));
});

Route::get('/report2', function () {
    return [
        'either' => DB::table('orders')->where('amount', '>', 100)->orWhere('status', 'new')->orderBy('id')->pluck('id'),
        'in' => DB::table('orders')->whereIn('user_id', [2])->pluck('id'),
        'notin' => DB::table('orders')->whereNotIn('status', ['paid'])->pluck('id'),
        'notnull' => DB::table('orders')->whereNotNull('status')->count(),
    ];
});

Route::get('/joined', function () {
    return DB::table('orders')
        ->join('users', 'orders.user_id', '=', 'users.id')
        ->where('orders.status', 'paid')
        ->orderBy('orders.id')
        ->get();
});

Route::get('/joined-count', function () {
    return ['n' => DB::table('orders')->leftJoin('users', 'orders.user_id', '=', 'users.id')->count()];
});
