<x-alert type="warn" :title="$user->name">{{ count($orders) }} orders</x-alert>
<x-alert/>
<ol>
@foreach($orders as $o)
  <li data-i="{{ $loop->index }}">{{ $loop->iteration }}/{{ $loop->count }} {{ $o->status }}@if($loop->last) (last)@endif</li>
@endforeach
</ol>
