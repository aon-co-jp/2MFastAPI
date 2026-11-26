<?php
return new class extends Migration {
    public function up(): void
    {
        Schema::create('roles', function (Blueprint $table) {
            $table->id();
            $table->string('name');
        });
        Schema::create('role_user', function (Blueprint $table) {
            $table->foreignId('user_id');
            $table->foreignId('role_id');
            $table->string('granted_by')->nullable();
        });
    }
};
