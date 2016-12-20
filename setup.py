from setuptools import setup, find_packages
import os, sys, shutil, getpass, glob, time

SETUP_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(os.path.join(SETUP_DIR, 'tools'), '')

print('Terminate br06_service...')
if 'serverupdate' in sys.argv:
    os.system('pkill -f br06_monitor')
    os.system('pkill -f treefrog')
    os.system('pkill -f FingerprintService')
else:
    if os.system('service br06_service stop'):
        os.system('pkill -f br06_monitor')
        os.system('pkill -f treefrog')
        os.system('pkill -f FingerprintService')
        os.system('service httpd stop')
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)

def change_permission(directory, permission):
    try:
        if os.path.isdir(directory):
            for dirname, subdirs, files in os.walk(directory):
                name = dirname
                os.chmod(name, permission)
                for filename in files:
                    name = os.path.join(dirname, filename)
                    os.chmod(name, permission)
        else:
            name = directory
            os.chmod(name, permission)
        print('Change permissions of {0} to {1}'.format(name, oct(permission)[2:]))
        return 0
    except:
        print('Can not change directory or file permissions, please try "chmod {0} {1}"'.format(oct(permission)[2:], name))
        return -1

if not 'serverupdate' in sys.argv:
    os.system('rpm -ivh {0}mysql-community-release-el7-5.noarch.rpm'.format(TOOLS_DIR))
    if os.system('yum install -y mysql-devel') or \
            os.system('yum install -y mysql-server') or \
            os.system('systemctl start mysqld') or \
            os.system('mysql_secure_installation'):
        print('Can not install mysql')
        exit(-1)

    setup(
        name = "br06_setup",
        install_requires = ['Django == 1.9.4', 'mysqlclient', 'django-nose', 'django-nocaptcha-recaptcha', 'django-bootstrap3', 'pytz', 'psutil', 'requests', 'django-crontab'],
        description = "install: django, mysqlclient, django-nose, django-nocaptcha-recaptcha, django-bootstrap3, pytz, psutil, requests",
    )

    import MySQLdb
    try:
        databasename = 'br06_db'
        db = MySQLdb.connect(host = 'localhost', user = 'root', passwd = '1')
        cursor = db.cursor()
        cursor.execute('show databases;')
        if databasename not in [x[0] for x in cursor.fetchall()]:
            cursor.execute('create database {0} default character set utf8;'.format(databasename))
            print('Create database {0} successfully'.format(databasename))
        else:
            print('Database {0} exists'.format(databasename))
    except:
        print('Create database {0} fail, please try "mysql -uroot -p" to create database and re-run "python3.4 setup.py install"'.format(databasename))
        exit(-1)
    finally:
        cursor.close()

    if os.system('python3.4 br06/manage.py makemigrations') or os.system('python3.4 br06/manage.py migrate'):
        print('Can not migrate database')
        exit(-1)

    if os.path.exists('/etc/yum.repos.d/CentOS-Media.repo') and os.system('mv /etc/yum.repos.d/CentOS-Media.repo /etc/yum.repos.d/CentOS-Media.repo.bak'):
        print('Can not remove CentOS-Media.repo')
        exit(-1)

    if os.system('yum install -y epel-release') or \
            os.system('yum localinstall -y --nogpgcheck {0}TCIT/nux-dextop-release-0-1.el7.nux.noarch.rpm'.format(TOOLS_DIR)) or \
            os.system('yum install -y vlc') or \
            os.system('yum install -y vlc-plugin-*'):
        print('Can not install VLC')
        exit(-1)

    if os.system('cp {0}mongodb.repo /etc/yum.repos.d/mongodb.repo'.format(TOOLS_DIR)) or \
            os.system('yum install -y mongodb-org'):
        print('Can not install mongodb')
        exit(-1)

    os.system('service mongod restart')
    if os.system('firewall-cmd --permanent --add-port=8800/tcp') or \
            os.system('firewall-cmd --add-port=8800/tcp'):
        print('Firewall opened fail')
        exit(-1)

    if os.system('yum install -y httpd httpd-devel') or os.system('systemctl enable httpd'):
        print('Can not install apache')
        exit(-1)

    with open('/etc/crontab', 'r+') as fd:
        add_string = '*/5  *  *  *  * root cd /var/www/br06 && /var/www/br06/systembackup/br06backup.sh >> /var/www/br06/systembackup/log/autobackup.log 2>&1'
        if fd.read().find(add_string) == -1:
            print('Writing backup information to /etc/crontab')
            fd.write(add_string + '\n')

    with open('/etc/sysconfig/selinux', 'r+') as fd:
        if fd.read().find('SELINUX=enforcing') != -1:
            fd.seek(0)
            fd_new = ['SELINUX=disabled\n' if line.strip().find('SELINUX=enforcing') == 0 else line for line in fd]
            fd.seek(0)
            fd.writelines(fd_new)
            print('Disable SELINUX')

    OLDPWD = os.getcwd()
    os.chdir('{0}mod_wsgi'.format(TOOLS_DIR))
    if os.system('sh configure --with-python=/usr/local/bin/python3.4') or \
            os.system('LD_RUN_PATH=/usr/local/lib make -j4 && make install -j4'):
        print('Can not install mod_wsgi')
        exit(-1)
    os.chdir(OLDPWD)

    if os.system('yum install -y lftp'):
        print('Can not install lftp')
        exit(-1)

OLDPWD = os.getcwd()
os.chdir('{0}TCIT'.format(TOOLS_DIR))
try:
    TCIT_old_dir = '/opt/TCIT_old'
    old_number = 1
    if os.path.exists('/opt/TCIT'):
        print('Backup the data...')
        while True:
            if not os.path.exists(TCIT_old_dir):
                break
            TCIT_old_dir = '/opt/TCIT_old-{0}'.format(old_number)
            old_number += 1
        shutil.move('/opt/TCIT', TCIT_old_dir)
    print('Install new TCIT and import the data...')
    for path in glob.glob('{0}TCIT/LocalAPI*'.format(TOOLS_DIR)):
        if os.path.isdir(path):
            print('New TCIT directory exists, remove TCIT directory')
            shutil.rmtree(path)
    if not os.system('tar zxvf LocalAPI*.tar.gz'):
        for path in glob.glob('{0}TCIT/LocalAPI*'.format(TOOLS_DIR)):
            if os.path.isdir(path) and path.find('LocalAPI') != -1:
                print('Move new TCIT directory to /opt/')
                shutil.move(path, '/opt/TCIT')
                tcit_bin_dir = '/opt/TCIT/bin'
                for dirname, subdirs, files in os.walk('{0}TCIT/bin'.format(TOOLS_DIR)):
                    dst = os.path.join(tcit_bin_dir, dirname[len('{0}TCIT/bin/'.format(TOOLS_DIR)):])
                    for subdirname in subdirs:
                        if not os.path.exists(os.path.join(dst, subdirname)):
                            shutil.copy(os.path.join(dirname, subdirname), dst)
                    for filename in files:
                        if not os.path.exists(os.path.join(dst, filename)):
                            shutil.copy(os.path.join(dirname, filename), dst)
                for path in glob.glob('{0}/*.lic'.format(TCIT_old_dir)):
                    try:
                        shutil.copy(path, '/opt/TCIT')
                    except:
                        pass
                if not change_permission('/opt/TCIT/bin', 0o755):
                    print('Remove old TCIT')
                    if os.path.exists(TCIT_old_dir):
                        shutil.rmtree(TCIT_old_dir)
                    raise Exception(0)
    raise Exception(-1)
except Exception as e:
    try:
        if int(str(e)):
            print('Install new TCIT error, please install TCIT manually')
    except:
        print(e)
        exit(-1)
os.chdir(OLDPWD)

if os.path.exists('/var/www/br06'):
    if os.path.exists('/var/www/br06_old'):
        print('The old br06 directory exists, remove old br06')
        shutil.rmtree('/var/www/br06_old')
    print('Backup the data...')
    shutil.move('/var/www/br06', '/var/www/br06_old')
    print('Install new br06 and import the data...')
    shutil.copytree(os.path.join(SETUP_DIR, 'br06'), '/var/www/br06')
    if os.system('cp /var/www/br06_old/config.ini /var/www/br06/') or \
            os.system('cp /var/www/br06_old/systembackup/backup.conf /var/www/br06/systembackup') or \
            os.system('cp /var/www/br06_old/systembackup/picsave.conf /var/www/br06/systembackup') or \
            os.system('cp -R /var/www/br06_old/media/facepic /var/www/br06/media') or \
            os.system('cp -R /var/www/br06_old/media/fruserpic /var/www/br06/media') or \
            os.system('cp -R /var/www/br06_old/media/logsetting /var/www/br06/media'):
        print('Install br06 fail, please manually install.')
        shutil.rmtree('/var/www/br06')
        shutil.move('/var/www/br06_old', '/var/www/br06')
        exit(-1)
    print('Remove old br06...')
    shutil.rmtree('/var/www/br06_old')
else:
    print('Install br06')
    shutil.copytree(os.path.join(SETUP_DIR, 'br06'), '/var/www/br06')

sys.path.append('/var/www/br06')
sys.path.append('/var/www/br06/br06')
from settings import EN_4G
if EN_4G:
    print('Install 4G')
    OLDPWD = os.getcwd()
    os.chdir('/var/www/br06')
    if os.system('python3.4 manage.py crontab add'):
        print('Add django crontab fail')
        exit(-1)
    os.chdir(OLDPWD)

if change_permission('/var/www/br06', 0o755):
    exit(-1)

if os.path.exists('/etc/udev/rules.d/70-persistent-finger.rules'):
    print('Remove old 70-persistent-finger.rules')
    os.remove('/etc/udev/rules.d/70-persistent-finger.rules')
print('Copy 70-persistent-finger.rules to /etc/udev/rules.d/')
shutil.copyfile(os.path.join(TOOLS_DIR, 'fingerprint/70-persistent-finger.rules'), '/etc/udev/rules.d/70-persistent-finger.rules')

if os.path.exists('/opt/br06_monitor'):
    print('Remove old br06_monitor')
    os.remove('/opt/br06_monitor')
print('Copy br06_monitor to /opt')
shutil.copyfile(os.path.join(TOOLS_DIR, 'br06_monitor'), '/opt/br06_monitor')
if change_permission('/opt/br06_monitor', 0o755):
    exit(-1)

if os.path.exists('/etc/init.d/br06_service'):
    print('Remove old br06_service')
    os.remove('/etc/init.d/br06_service')
print('Copy br06_service to /etc/init.d/')
shutil.copyfile(os.path.join(TOOLS_DIR, 'br06_service'), '/etc/init.d/br06_service')
if change_permission('/etc/init.d/br06_service', 0o755):
    exit(-1)
if os.system('chkconfig --add /etc/init.d/br06_service') or os.system('chkconfig --level 35 br06_service on'):
    print('Can not enable br06_service')
    exit(-1)

if os.path.exists('/etc/httpd/conf.d/br06.conf'):
    print('Remove old br06.conf')
    os.remove('/etc/httpd/conf.d/br06.conf')
print('Copy br06.conf to /etc/httpd/conf.d/')
shutil.copyfile(os.path.join(TOOLS_DIR, 'br06.conf'), '/etc/httpd/conf.d/br06.conf')

try:
    os.mkdir('/opt/backup')
    os.chmod('/opt/backup', 0o777)
    print('Make directory /opt/backup')
except FileExistsError:
    pass
except:
    print('Can not make directory, please try "mkdir -m 777 /opt/backup"')
    exit(-1)

if change_permission('/var/www/br06/logs', 0o777):
    exit(-1)
else:
    print('Change permissions of /var/www/br06/logs to 777')

if not os.path.exists('/var/log/br06/update.log'):
    os.system('mkdir -m 777 /var/log/br06')
    if os.system('touch /var/log/br06/update.log') or os.system('chmod 777 /var/log/br06/update.log'):
        print('Create update.log failed!')

if change_permission('/var/www/br06/media', 0o777):
    exit(-1)
else:
    print('Change permissions of /var/www/br06/media to 777')

if change_permission('/var/www/br06/systembackup', 0o777):
    exit(-1)
else:
    print('Change permissions of /var/www/br06/systembackup to 777')

if 'serverupdate' in sys.argv:
    newpid = os.fork()
    if newpid == 0:
        time.sleep(3)
        print('Restart the system.')
        if os.system('service br06_service start'):
            print('Start br06 failed.')
            exit(-1)
        if os.system('service httpd restart'):
            print('Restart httpd failed.')
            exit(-1)
else:
    reboot = input('Successful installation. Enter "y" to reboot now or "n" to manually reboot later (y/n): ')
    while True:
        if reboot == 'y' or reboot == 'Y':
            if os.system('reboot'):
                print('System reboot fail, please reboot manually.')
            break
        elif reboot == 'n' or reboot == 'N':
            break
        else:
            reboot = input('Please enter "y" to reboot now or "n" to manually reboot later (y/n): ')
print()
exit(0)
