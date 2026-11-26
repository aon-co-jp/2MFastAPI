<?php
namespace App\Models;

class User extends Model
{
    protected $fillable = ['name', 'email'];

    public function orders()
    {
        return $this->hasMany(Order::class);
    }
}
