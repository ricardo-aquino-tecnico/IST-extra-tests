/* Aplicação de teste: observa a VM; não implementa o CloudIST. */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static double seconds(clockid_t clock_id) {
    struct timespec now;
    clock_gettime(clock_id, &now);
    return (double)now.tv_sec + (double)now.tv_nsec / 1000000000.0;
}

static int copied_at(const char *directory) {
    struct stat info;
    if (lstat(directory, &info) || !S_ISDIR(info.st_mode)) return 0;
    if (!CHECK_CONTENT) return 1;
    char name[8192], data[64] = {0};
    snprintf(name, sizeof(name), "%s/text.txt", directory);
    int fd = open(name, O_RDONLY);
    if (fd < 0) return 0;
    ssize_t size = read(fd, data, sizeof(data)-1);
    close(fd);
    if (size != (ssize_t)strlen("CloudIST\nsecond line\n") || strcmp(data, "CloudIST\nsecond line\n")) return 0;
    snprintf(name,sizeof(name),"%s/nested/deep/level3/level4/level5/dados.bin",directory);
    fd=open(name,O_RDONLY);
    if(fd<0)return 0;
    unsigned char bytes[512];
    size_t offset=0;
    ssize_t count;
    while((count=read(fd,bytes,sizeof(bytes)))>0) {
        for(ssize_t i=0;i<count;i++) if(bytes[i]!=(unsigned char)((offset+(size_t)i)%256)){close(fd);return 0;}
        offset+=(size_t)count;
    }
    close(fd);
    return count==0 && offset==20736;
}

static int copied(void) {
    char directories[4096];
    snprintf(directories,sizeof(directories),"%s",COPY_DIR);
    char *state=NULL;
    for(char *part=strtok_r(directories,"|",&state);part;part=strtok_r(NULL,"|",&state))
        if(copied_at(part))return 1;
    return 0;
}

static void record(const char *event, int ready) {
    struct rlimit ram, disk;
    getrlimit(RLIMIT_AS, &ram);
    getrlimit(RLIMIT_FSIZE, &disk);
    char line[1024];
    int size = snprintf(line, sizeof(line),
        "{\"event\":\"%s\",\"tag\":\"%s\",\"pid\":%ld,\"ppid\":%ld,"
        "\"time\":%.9f,\"cpu\":%.9f,\"ready\":%d,\"exit\":%d,"
        "\"ram_soft\":%llu,\"ram_hard\":%llu,\"disk_soft\":%llu,\"disk_hard\":%llu}\n",
        event, APP_TAG, (long)getpid(), (long)getppid(), seconds(CLOCK_MONOTONIC),
        seconds(CLOCK_PROCESS_CPUTIME_ID), ready, RAISE_SIGNAL ? -RAISE_SIGNAL : EXIT_CODE,
        (unsigned long long)ram.rlim_cur, (unsigned long long)ram.rlim_max,
        (unsigned long long)disk.rlim_cur, (unsigned long long)disk.rlim_max);
    int fd = open(TRACE_FILE, O_WRONLY | O_CREAT | O_APPEND, 0600);
    if (fd < 0 || write(fd, line, (size_t)size) != size) _exit(125);
    close(fd);
}

static int cpu_spy(int argc, char **argv) {
    if (argc < 7) return 124;
    int program = argc-1;
    double percent = -1;
    for (int i=4; i<argc; i++) {
        if ((!strcmp(argv[i], "-l") || !strcmp(argv[i], "--limit")) && i+1<argc)
            percent = strtod(argv[++i], NULL);
        else if (!strcmp(argv[i], "--") && i+1<argc) { program=i+1; break; }
    }
    const char *name = strrchr(argv[program], '/');
    name = name ? name+1 : argv[program];
    if (!strncmp(name,"probe_",6)) name+=6;
    char line[512];
    int size = snprintf(line,sizeof(line),"{\"tag\":\"%s\",\"percent\":%.9g}\n",name,percent);
    int fd = open(argv[2],O_WRONLY|O_CREAT|O_APPEND,0600);
    if (fd < 0 || write(fd,line,(size_t)size) != size) return 125;
    close(fd);
    if (argv[3][0]) execv(argv[3],argv+3);
    else execv(argv[program],argv+program);
    return 126;
}

int main(int argc, char **argv) {
    if (argc > 1 && !strcmp(argv[1],"--spy")) return cpu_spy(argc,argv);
    int ready = copied();
    record("start", ready);
    double until = seconds(CLOCK_PROCESS_CPUTIME_ID) + (double)BUSY_MS / 1000.0;
    while (seconds(CLOCK_PROCESS_CPUTIME_ID) < until) { }
    struct timespec delay = { SLEEP_MS / 1000, (SLEEP_MS % 1000) * 1000000L };
    while (nanosleep(&delay, &delay) < 0 && errno == EINTR) { }
    record("end", ready);
    if (RAISE_SIGNAL) raise(RAISE_SIGNAL);
    return EXIT_CODE;
}
