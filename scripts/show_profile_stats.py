from pstats import Stats


stats = Stats('/Users/Harold/Desktop/profileData')
stats.strip_dirs()
stats.sort_stats('cumulative')
stats.print_stats()
