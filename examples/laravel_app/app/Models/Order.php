<?php
namespace App\Models;

class Order extends Model
{
    protected $table = 'orders';

    public function user()
    {
        return $this->belongsTo(User::class);
    }
}
