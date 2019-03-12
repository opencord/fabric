# Copyright 2017-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2019-03-12 22:39
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('fabric', '0002_auto_20190305_0238'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fabricipaddress',
            name='backend_status',
            field=models.CharField(default=b'Provisioning in progress', max_length=1024),
        ),
        migrations.AlterField(
            model_name='fabricipaddress',
            name='ip',
            field=models.CharField(help_text=b'The unique IP address (either IPv4 or IPv6 / netmask)', max_length=52),
        ),
        migrations.AlterField(
            model_name='fabricipaddress',
            name='leaf_model_name',
            field=models.CharField(help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024),
        ),
        migrations.AlterField(
            model_name='fabricipaddress',
            name='updated',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer'),
        ),
        migrations.AlterField(
            model_name='nodetoswitchport',
            name='backend_status',
            field=models.CharField(default=b'Provisioning in progress', max_length=1024),
        ),
        migrations.AlterField(
            model_name='nodetoswitchport',
            name='leaf_model_name',
            field=models.CharField(help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024),
        ),
        migrations.AlterField(
            model_name='nodetoswitchport',
            name='updated',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer'),
        ),
        migrations.AlterField(
            model_name='portinterface',
            name='backend_status',
            field=models.CharField(default=b'Provisioning in progress', max_length=1024),
        ),
        migrations.AlterField(
            model_name='portinterface',
            name='leaf_model_name',
            field=models.CharField(help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024),
        ),
        migrations.AlterField(
            model_name='portinterface',
            name='name',
            field=models.CharField(help_text=b'The unique name of the fabric switch port', max_length=254),
        ),
        migrations.AlterField(
            model_name='portinterface',
            name='updated',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer'),
        ),
        migrations.AlterField(
            model_name='switch',
            name='backend_status',
            field=models.CharField(default=b'Provisioning in progress', max_length=1024),
        ),
        migrations.AlterField(
            model_name='switch',
            name='driver',
            field=models.CharField(default=b'ofdpa3', help_text=b'The driver used by the SDN controller', max_length=254),
        ),
        migrations.AlterField(
            model_name='switch',
            name='ipv4Loopback',
            field=models.CharField(help_text=b'Fabric loopback interface', max_length=17),
        ),
        migrations.AlterField(
            model_name='switch',
            name='leaf_model_name',
            field=models.CharField(help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024),
        ),
        migrations.AlterField(
            model_name='switch',
            name='name',
            field=models.CharField(help_text=b'The unique name of the fabric switch', max_length=254),
        ),
        migrations.AlterField(
            model_name='switch',
            name='ofId',
            field=models.CharField(help_text=b'The unique OpenFlow ID of the fabric switch', max_length=19),
        ),
        migrations.AlterField(
            model_name='switch',
            name='routerMac',
            field=models.CharField(help_text=b'MAC address of the fabric switch used for all interfaces', max_length=17),
        ),
        migrations.AlterField(
            model_name='switch',
            name='updated',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer'),
        ),
        migrations.AlterField(
            model_name='switchport',
            name='backend_status',
            field=models.CharField(default=b'Provisioning in progress', max_length=1024),
        ),
        migrations.AlterField(
            model_name='switchport',
            name='leaf_model_name',
            field=models.CharField(help_text=b'The most specialized model in this chain of inheritance, often defined by a service developer', max_length=1024),
        ),
        migrations.AlterField(
            model_name='switchport',
            name='updated',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text=b'Time this model was changed by a non-synchronizer'),
        ),
    ]
