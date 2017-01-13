/**
 * Finds the index of the last element of array a that is less than or equal
 * to x. The array must not be empty and its elements must be in nondecreasing
 * order.
 */
function findLastLE(a, x) {
	
	if (x < a[0])
		return -1;
	
	else {
		
		let low = 0;
		let high = a.length;
		let mid;
		
		// invariant: result is in [low, high)
		
		while (high != low + 1) {
			
			mid = Math.floor((low + high) / 2);
			
			if (a[mid] <= x)
				low = mid;
			else
				high = mid;
				
		}
		
		return low;
		
	}
	
}
