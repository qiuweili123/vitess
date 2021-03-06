# Copyright 2013, Google Inc. All rights reserved.
# Use of this source code is governed by a BSD-style license that can
# be found in the LICENSE file.

"""A Vitess keyspace represents a sharded MySQL database."""

import struct

from vtdb import keyrange_constants


pack_keyspace_id = struct.Struct('!Q').pack


class Keyspace(object):
  """Represent the SrvKeyspace object from the toposerver.

  Provide functions to extract sharding information from the same.
  """

  # load this object from a SrvKeyspace object generated by vt
  def __init__(self, name, data):
    self.name = name
    self.partitions = data.get('Partitions', {})
    self.sharding_col_name = data.get('ShardingColumnName', '')
    self.sharding_col_type = data.get(
        'ShardingColumnType', keyrange_constants.KIT_UNSET)
    self.served_from = data.get('ServedFrom', None)

  def get_shards(self, db_type):
    if not db_type:
      raise ValueError('db_type is not set')
    try:
      return self.partitions[db_type]['ShardReferences']
    except KeyError:
      return []

  def get_shard_count(self, db_type):
    if not db_type:
      raise ValueError('db_type is not set')
    shards = self.get_shards(db_type)
    return len(shards)

  def get_shard_names(self, db_type):
    if not db_type:
      raise ValueError('db_type is not set')
    shards = self.get_shards(db_type)
    return [shard['Name'] for shard in shards]

  def keyspace_id_to_shard_name_for_db_type(self, keyspace_id, db_type):
    """Finds the shard for a keyspace_id.

    WARNING: this only works for KIT_UINT64 keyspace ids.

    Args:
      keyspace_id: A uint64 keyspace_id.
      db_type: Str tablet type (master, rdonly, or replica).

    Returns:
      Shard name.

    Raises:
      ValueError: On invalid keyspace_id.
    """
    if not keyspace_id:
      raise ValueError('keyspace_id is not set')
    if not db_type:
      raise ValueError('db_type is not set')
    # Pack this into big-endian and do a byte-wise comparison.
    pkid = pack_keyspace_id(keyspace_id)
    shards = self.get_shards(db_type)
    for shard in shards:
      if 'KeyRange' not in shard or not shard['KeyRange']:
        # this keyrange is covering the full space
        return shard['Name']
      if _shard_contain_kid(pkid,
                            shard['KeyRange']['Start'],
                            shard['KeyRange']['End']):
        return shard['Name']
    raise ValueError(
        'cannot find shard for keyspace_id %s in %s' % (keyspace_id, shards))


def _shard_contain_kid(pkid, start, end):
  return start <= pkid and (end == keyrange_constants.MAX_KEY or pkid < end)
