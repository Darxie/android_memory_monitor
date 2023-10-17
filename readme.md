# Readme

## Why are we using the PSS metric instead of RSS?

When monitoring memory usage of your app on Android, the two common metrics are PSS (Proportional Set Size) and RSS (Resident Set Size). Each provides valuable information, but for app optimization purposes on Android, PSS is typically the more useful metric. Here's why:

### PSS (Proportional Set Size)

Definition: PSS represents the amount of memory used by an application, where shared memory is divided proportionally among the apps using that memory. In other words, if three apps are using a shared memory segment of 3 MB, that 3 MB would only count as 1 MB for each app's PSS.

Relevance: This is especially useful for Android because many processes (apps) often share memory due to the Android runtime, system processes, and common libraries. PSS gives a more realistic measure of the memory footprint of an app, accounting for this shared memory.

Use Case: PSS is often the metric of choice when you're concerned about the overall memory usage impact of your app on the system.

### RSS (Resident Set Size)

Definition: RSS is the portion of application memory that is held in RAM. Unlike PSS, it doesn't account for shared memory in a proportional way. So, if three apps are sharing a memory segment of 3 MB, that 3 MB would count in its entirety for each of the three apps, which can be misleading.

Relevance: While RSS can give a snapshot of how much memory is currently resident in RAM for an app, it can provide an inflated and potentially misleading view of an app's actual memory cost to the system, especially when shared libraries are in use.

### Conclusion

For app developers, especially when optimizing for memory usage, PSS is generally the preferred metric. This is because it more accurately represents the memory cost of your app to the overall system. If you're trying to assess how your app behaves in a memory-constrained environment or aiming to minimize its impact on system resources, PSS provides a clearer picture.
